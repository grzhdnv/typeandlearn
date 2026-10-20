"""Test real HTTP routes, NLP, background processing, and SQLite persistence.

Only the external LLM and dictionary responses are replaced with fixtures.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from fastapi import testclient
from pydantic_ai import models as ai_models
import sqlmodel

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

# Application wiring must never use local credentials or the user's database.
with mock.patch.dict(os.environ, {
    "DEEPSEEK_API_KEY": "test-only-not-a-real-key",
    "DATABASE_URL": "sqlite://",
}):
    import app
    import app_state
    from api.routes import texts
    from core import database
    from repositories import job_repository, text_repository
    from schemas import texts as schemas
    from services import dictionary_service
    from services import llm_service
    from services import preprocessing_service
    from services import text_service


class TextApiTests(unittest.TestCase):
    """Run the public text lifecycle against an isolated on-disk database."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = sqlmodel.create_engine(
            f"sqlite:///{directory}/test.sqlite",
            connect_args={"check_same_thread": False},
        )
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        llm = mock.Mock(spec=llm_service.LlmService)
        self.llm = llm
        llm.extract_metadata.return_value = schemas.GeneratedMetadata(
            title="Test garden", difficulty_level="A1", language="German"
        )
        llm.translate_sentence_async = mock.AsyncMock(
            return_value=schemas.SentenceTranslation(
                translation="A test translation.",
                translation_hints=[schemas.HintGroup(
                    words=["Hund"], hint="dog"
                )],
            )
        )
        llm.generate_practice_sentences_async = mock.AsyncMock(
            return_value=schemas.PracticeSentencesResponse.model_validate({
                "sentences": [{
                    "sentence": "Der Hund spielt.",
                    "translation": "The dog plays.",
                    "translation_hints": [],
                }],
            })
        )
        dictionary = mock.Mock(spec=dictionary_service.DictionaryService)
        dictionary.translate_word.return_value = "A test definition."
        self.preprocessing = preprocessing_service.PreprocessingService()
        self.job_repo = job_repository.JobRepository(self.engine)
        service = text_service.TextService(
            text_repository.TextRepository(self.engine),
            llm,
            self.preprocessing,
            dictionary,
            job_repository=self.job_repo,
        )
        self.enterContext(mock.patch.object(database, "engine", self.engine))
        self.enterContext(mock.patch.object(app_state, "text_service", service))
        self.enterContext(mock.patch.object(texts, "text_service", service))
        self.enterContext(mock.patch.object(
            ai_models, "ALLOW_MODEL_REQUESTS", False
        ))
        self.client = self.enterContext(testclient.TestClient(app.app))

    def _upload(self) -> str:
        response = self.client.post("/texts", json={
            "text": "Der kleine Hund läuft im Garten. Die Sonne scheint.",
            "language": "German",
        })
        self.assertEqual(response.status_code, 200, response.text)
        return self.client.get("/texts/titles").json()["titles"][0]["id"]

    def test_upload_processing_practice_progress_and_crud(self) -> None:
        text_id = self._upload()
        path = f"/texts/{text_id}"
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["total_sentences"], 2)

        # Verify durable background job was created and marked completed
        jobs = self.job_repo.load_jobs_by_text(int(text_id), "owner_local_default")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].task_type, "process_text")
        self.assertEqual(jobs[0].status, "completed")
        self.assertTrue(data["original_paragraphs"][0]["sentences"][0][
            "translation"
        ])
        self.assertEqual(len(data["practice_sentences"]), 1)
        self.assertTrue(data["top_words"][0]["translation"])

        for index, completed in ((0, 1), (0, 1), (1, 2)):
            response = self.client.post(
                f"{path}/progress", json={"sentence_index": index}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["completed_sentences"], completed)
        titles = self.client.get("/texts/titles").json()["titles"]
        self.assertEqual(titles[0]["completed_sentences"], 2)

        response = self.client.patch(path, json={"category": "Test", "author": "Test author"})
        self.assertEqual(response.json()["data"]["category"], "Test")
        titles = self.client.get("/texts/titles").json()["titles"]
        self.assertEqual(titles[0]["author"], "Test author")
        self.assertEqual(titles[0]["category"], "Test")
        response = self.client.post(f"{path}/reset")
        self.assertEqual(response.json()["completed_sentences"], 0)
        response = self.client.post(f"{path}/regenerate-words")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get(path).json()["data"]["status"],
                         "processed")

        self.assertEqual(self.client.delete(path).status_code, 200)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get("/texts/titles").json()["titles"], [])

    def test_failed_translation_is_visible_and_retry_preserves_original(self) -> None:
        self.llm.translate_sentence_async.side_effect = RuntimeError("Provider unavailable")
        text_id = self._upload()
        path = f"/texts/{text_id}"
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["enrichment_stage"], "failed")
        self.assertIn("could not be translated", data["error_message"])
        self.assertEqual(data["total_sentences"], 2)
        self.llm.generate_practice_sentences_async.assert_not_called()

        self.llm.translate_sentence_async.side_effect = None
        self.assertEqual(self.client.post(f"{path}/retry").status_code, 200)
        self.assertEqual(self.client.get(path).json()["data"]["status"], "processed")

    def test_failed_practice_generation_is_not_reported_as_completed(self) -> None:
        self.llm.generate_practice_sentences_async.side_effect = RuntimeError("Provider unavailable")
        text_id = self._upload()
        data = self.client.get(f"/texts/{text_id}").json()["data"]
        self.assertEqual(data["status"], "failed")
        self.assertIn("could not be generated", data["error_message"])
        self.assertTrue(data["original_paragraphs"][0]["sentences"][0]["translation"])

    def test_intake_without_provider_requires_explicit_language(self) -> None:
        self.llm.extract_metadata.side_effect = RuntimeError("No provider configured")
        response = self.client.post("/texts", json={"text": "Hallo Welt."})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Choose German", response.json()["detail"])
        self.assertEqual(self.client.get("/texts/titles").json()["titles"], [])
        response = self.client.post("/texts", json={"text": "Hallo Welt.", "language": "german"})
        self.assertEqual(response.status_code, 200)
        data = self.client.get(f"/texts/{response.json()['id']}").json()["data"]
        self.assertEqual(data["language"], "German")

    def test_progress_rejects_invalid_indices_and_exposes_resume_positions(self) -> None:
        text_id = self._upload()
        path = f"/texts/{text_id}"
        for invalid_index in (-1, 2, 100):
            self.assertEqual(self.client.post(f"{path}/progress", json={"sentence_index": invalid_index}).status_code, 400)
        self.client.post(f"{path}/progress", json={"sentence_index": 1})
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["completed_sentences"], 1)
        self.assertEqual(data["completed_sentence_indices"], [1])

    def test_terminal_status_overrides_stale_enrichment_stage(self) -> None:
        text_id = self._upload()
        path = f"/texts/{text_id}"

        # Simulate legacy rows whose stage stayed "queued" after processing
        repository = text_repository.TextRepository(self.engine)
        record = repository.load_one_text(int(text_id), "owner_local_default")
        assert record is not None
        record.enrichment_stage = "queued"
        repository.update_text(record)

        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["enrichment_stage"], "completed")

        titles = self.client.get("/texts/titles").json()["titles"]
        self.assertEqual(titles[0]["enrichment_stage"], "completed")

    def test_upload_infers_all_metadata_when_client_provides_only_text(self) -> None:
        self.llm.extract_metadata.return_value = schemas.GeneratedMetadata(
            title="Inferred title",
            difficulty_level="B1",
            language="French",
            author="Inferred author",
            category="Fairy Tale",
        )
        response = self.client.post("/texts", json={
            "text": "Le petit chat dort. Il rêve.",
        })
        self.assertEqual(response.status_code, 200, response.text)

        text_id = self.client.get("/texts/titles").json()["titles"][0]["id"]
        data = self.client.get(f"/texts/{text_id}").json()["data"]
        self.assertEqual(data["language"], "French")
        self.assertEqual(data["title"], "Inferred title")
        self.assertEqual(data["difficulty_level"], "B1")
        self.assertEqual(data["author"], "Inferred author")
        self.assertEqual(data["category"], "Fairy Tale")

    def test_client_provided_metadata_wins_over_inference(self) -> None:
        self.llm.extract_metadata.return_value = schemas.GeneratedMetadata(
            title="Inferred title",
            difficulty_level="B1",
            language="French",
            author="Inferred author",
            category="Inferred category",
        )
        response = self.client.post("/texts", json={
            "text": "Der Hund läuft.",
            "language": "German",
            "title": "Client title",
        })
        self.assertEqual(response.status_code, 200, response.text)

        text_id = self.client.get("/texts/titles").json()["titles"][0]["id"]
        data = self.client.get(f"/texts/{text_id}").json()["data"]
        self.assertEqual(data["language"], "German")
        self.assertEqual(data["title"], "Client title")
        self.assertEqual(data["difficulty_level"], "B1")
        self.assertEqual(data["author"], "Inferred author")
        self.assertEqual(data["category"], "Inferred category")

    def test_upload_response_includes_text_id(self) -> None:
        response = self.client.post("/texts", json={
            "text": "Der Hund läuft.",
            "language": "German",
        })
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIsInstance(payload["id"], int)
        titles = self.client.get("/texts/titles").json()["titles"]
        self.assertEqual(str(payload["id"]), titles[0]["id"])

    def test_patch_updates_title(self) -> None:
        text_id = self._upload()
        response = self.client.patch(
            f"/texts/{text_id}", json={"title": "Renamed by user"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["title"], "Renamed by user")

    def test_missing_model_returns_actionable_503_without_saving(self) -> None:
        with mock.patch.object(
            preprocessing_service.spacy, "load", side_effect=OSError("missing")
        ):
            response = self.client.post("/texts", json={
                "text": "Der Hund läuft.", "language": "German",
            })
        self.assertEqual(response.status_code, 503)
        self.assertIn("npm run bootstrap", response.json()["detail"])
        self.assertEqual(self.client.get("/texts/titles").json()["titles"], [])

    def test_regeneration_missing_model_preserves_existing_text(self) -> None:
        text_id = self._upload()
        path = f"/texts/{text_id}"
        before = self.client.get(path).json()["data"]
        with mock.patch.object(
            self.preprocessing, "process_text",
            side_effect=preprocessing_service.MissingLanguageModelError(
                "Run `npm run bootstrap`"
            ),
        ):
            response = self.client.post(f"{path}/regenerate-words")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.client.get(path).json()["data"], before)


if __name__ == "__main__":
    unittest.main()
