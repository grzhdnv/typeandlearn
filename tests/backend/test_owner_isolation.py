"""Multi-tenant ownership isolation integration tests.

Verifies that users cannot access, list, mutate, or delete records belonging
to other owners via the HTTP API layer (ADR-0002).
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from fastapi import testclient
import sqlmodel

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

with mock.patch.dict(os.environ, {
    "DEEPSEEK_API_KEY": "test-key-mock",
    "DATABASE_URL": "sqlite://",
}):
    import app
    import app_state
    from api.routes import texts
    from core import database
    from repositories import text_repository
    from schemas import texts as schemas
    from services import dictionary_service, llm_service, preprocessing_service, text_service


class OwnerIsolationTests(unittest.TestCase):
    """Verify strict tenant isolation across all endpoints."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = sqlmodel.create_engine(
            f"sqlite:///{directory}/test_isolation.sqlite",
            connect_args={"check_same_thread": False},
        )
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

        llm = mock.Mock(spec=llm_service.LlmService)
        llm.extract_metadata.return_value = schemas.GeneratedMetadata(
            title="Isolated Story", difficulty_level="A1"
        )
        llm.translate_sentence_async = mock.AsyncMock(
            return_value=schemas.SentenceTranslation(
                translation="A mock translation.",
                translation_hints=[],
            )
        )
        llm.generate_practice_sentences_async = mock.AsyncMock(
            return_value=schemas.PracticeSentencesResponse(
                sentences=[],
            )
        )
        dictionary = mock.Mock(spec=dictionary_service.DictionaryService)
        dictionary.translate_word.return_value = "Mock definition"
        preprocessing = preprocessing_service.PreprocessingService()

        service = text_service.TextService(
            text_repository.TextRepository(self.engine),
            llm,
            preprocessing,
            dictionary,
        )

        self.enterContext(mock.patch.object(database, "engine", self.engine))
        self.enterContext(mock.patch.object(app_state, "text_service", service))
        self.enterContext(mock.patch.object(texts, "text_service", service))
        self.client = self.enterContext(testclient.TestClient(app.app))

        self.owner_a_headers = {"X-Owner-Id": "user_alpha"}
        self.owner_b_headers = {"X-Owner-Id": "user_beta"}

    def test_complete_tenant_isolation(self) -> None:
        # 1. User A uploads a text
        upload_resp = self.client.post(
            "/texts",
            json={"text": "Hallo Welt. Wie geht es dir?", "language": "German"},
            headers=self.owner_a_headers,
        )
        self.assertEqual(upload_resp.status_code, 200)

        titles_a = self.client.get("/texts/titles", headers=self.owner_a_headers).json()["titles"]
        self.assertEqual(len(titles_a), 1)
        text_id_a = titles_a[0]["id"]

        # 2. User B queries texts -> should be completely empty (no data leakage)
        texts_b = self.client.get("/texts", headers=self.owner_b_headers).json()["data"]
        self.assertEqual(len(texts_b), 0)

        titles_b = self.client.get("/texts/titles", headers=self.owner_b_headers).json()["titles"]
        self.assertEqual(len(titles_b), 0)

        # 3. User B attempts direct access by ID -> 404 Not Found
        get_b = self.client.get(f"/texts/{text_id_a}", headers=self.owner_b_headers)
        self.assertEqual(get_b.status_code, 404)

        # 4. User B attempts to update User A's metadata -> 404
        patch_b = self.client.patch(
            f"/texts/{text_id_a}",
            json={"difficulty_level": "C2"},
            headers=self.owner_b_headers,
        )
        self.assertEqual(patch_b.status_code, 404)

        # 5. User B attempts to update progress on User A's text -> 404
        progress_b = self.client.post(
            f"/texts/{text_id_a}/progress",
            json={"sentence_index": 0},
            headers=self.owner_b_headers,
        )
        self.assertEqual(progress_b.status_code, 404)

        # 6. User B attempts to reset progress on User A's text -> 404
        reset_b = self.client.post(
            f"/texts/{text_id_a}/reset",
            headers=self.owner_b_headers,
        )
        self.assertEqual(reset_b.status_code, 404)

        # 7. User B attempts to delete User A's text -> 404
        delete_b = self.client.delete(f"/texts/{text_id_a}", headers=self.owner_b_headers)
        self.assertEqual(delete_b.status_code, 404)

        # Confirm User A's text still exists
        get_a = self.client.get(f"/texts/{text_id_a}", headers=self.owner_a_headers)
        self.assertEqual(get_a.status_code, 200)

        # 8. User B uploads their own text
        self.client.post(
            "/texts",
            json={"text": "Bonjour tout le monde.", "language": "French"},
            headers=self.owner_b_headers,
        )

        # Each user sees only their own text
        titles_a_after = self.client.get("/texts/titles", headers=self.owner_a_headers).json()["titles"]
        self.assertEqual(len(titles_a_after), 1)
        self.assertEqual(titles_a_after[0]["language"], "German")

        titles_b_after = self.client.get("/texts/titles", headers=self.owner_b_headers).json()["titles"]
        self.assertEqual(len(titles_b_after), 1)
        self.assertEqual(titles_b_after[0]["language"], "French")


if __name__ == "__main__":
    unittest.main()
