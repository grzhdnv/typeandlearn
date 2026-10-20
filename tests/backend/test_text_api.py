"""Test real HTTP routes, NLP, background processing, and SQLite persistence.

Only the external LLM and dictionary responses are replaced with fixtures.
"""

from __future__ import annotations

import os
from datetime import timedelta
import pathlib
import sys
import tempfile
import asyncio
import threading
import time
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
    from core.settings import Settings
    from worker import Worker
    from models.jobs import BackgroundJobRecord, utc_now
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
        llm.is_configured = True
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
        self.worker = Worker(self.job_repo, service, poll_interval=.02)
        self.enterContext(mock.patch.object(app_state, "job_repository", self.job_repo))
        self.enterContext(mock.patch.object(database, "engine", self.engine))
        self.enterContext(mock.patch.object(app_state, "text_service", service))
        self.enterContext(mock.patch.object(texts, "text_service", service))
        self.enterContext(mock.patch.object(
            ai_models, "ALLOW_MODEL_REQUESTS", False
        ))
        self.client = self.enterContext(testclient.TestClient(app.create_app(Settings(embedded_worker_enabled=False))))

    def _upload(self) -> str:
        response = self.client.post("/texts", json={
            "text": "Der kleine Hund läuft im Garten. Die Sonne scheint.",
            "language": "German",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.worker.process_one_job()
        return self.client.get("/texts/titles").json()["titles"][0]["id"]

    def test_upload_persists_source_and_job_without_nlp_or_provider_work(self) -> None:
        source = "Le petit chat dort. Il rêve."
        with mock.patch.object(self.preprocessing, "process_text") as preprocess:
            response = self.client.post("/texts", json={"text": source, "filtering_method": "llm"})
            self.assertEqual(response.status_code, 200)
            preprocess.assert_not_called()
        self.llm.extract_metadata.assert_not_called()
        self.llm.filter_meaningful_words.assert_not_called()
        self.llm.translate_sentence_async.assert_not_called()
        data = self.client.get(f"/texts/{response.json()['id']}").json()["data"]
        self.assertEqual(data["source_text"], source)
        self.assertEqual(data["original_paragraphs"], [])
        jobs = self.job_repo.load_jobs_by_text(response.json()["id"], "owner_local_default")
        self.assertEqual([(job.status, job.attempt_count) for job in jobs], [("pending", 0)])
        self.assertNotIn(source, str(jobs[0].payload))

    def test_original_ready_during_metadata_wait_and_user_edits_survive(self) -> None:
        started, release = threading.Event(), threading.Event()
        inferred = schemas.GeneratedMetadata(title="Inferred title", language="French", difficulty_level="B1")
        def metadata(*args, **kwargs):
            started.set()
            release.wait(10)
            return inferred
        self.llm.extract_metadata.side_effect = metadata
        response = self.client.post("/texts", json={"text": "Der Hund läuft. Die Sonne scheint.", "language": "German"})
        path = f"/texts/{response.json()['id']}"
        thread = threading.Thread(target=self.worker.process_one_job)
        thread.start()
        try:
            self.assertTrue(started.wait(10))
            data = self.client.get(path).json()["data"]
            self.assertEqual(data["enrichment_stage"], "analyzing_metadata")
            self.assertEqual(data["total_sentences"], 2)
            sentence_ids = [s.id for s in app_state.text_service._repository.load_sentences(response.json()["id"], "owner_local_default")]
            self.assertEqual(self.client.post(path+"/progress", json={"sentence_index": 0}).status_code, 200)
            self.assertEqual(self.client.patch(path, json={"title": "My chosen title"}).status_code, 200)
        finally:
            release.set()
            thread.join(15)
        self.assertFalse(thread.is_alive())
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["title"], "My chosen title")
        self.assertEqual(data["language"], "German")
        self.assertEqual(data["difficulty_level"], "B1")
        self.assertEqual(data["completed_sentence_indices"], [0])
        # Regeneration stays off the request path and never replaces sentence positions.
        with mock.patch.object(self.preprocessing, "process_text", wraps=self.preprocessing.process_text) as prepare:
            self.client.post(path+"/regenerate-words")
            prepare.assert_not_called()
            self.worker.process_one_job()
        self.assertEqual([s.id for s in app_state.text_service._repository.load_sentences(response.json()["id"], "owner_local_default")], sentence_ids)
        self.assertEqual(self.client.get(path).json()["data"]["completed_sentence_indices"], [0])

    def test_ai_regeneration_is_queued_and_failure_preserves_previous_vocabulary(self) -> None:
        text_id = self._upload()
        path = f"/texts/{text_id}"
        before = self.client.get(path).json()["data"]
        self.llm.filter_meaningful_words.side_effect = RuntimeError("Provider unavailable")
        response = self.client.post(path+"/regenerate-words", json={"filtering_method": "llm"})
        self.assertEqual(response.status_code, 200)
        self.llm.filter_meaningful_words.assert_not_called()
        self.worker.process_one_job()
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "failed")
        self.assertIn("AI word filtering is unavailable", data["error_message"])
        self.assertEqual(data["top_words"], before["top_words"])
        self.assertEqual(data["practice_sentences"], before["practice_sentences"])

    def test_failed_language_detection_retries_persisted_source(self) -> None:
        self.llm.extract_metadata.side_effect = RuntimeError("Provider unavailable")
        source = "Le petit chat dort."
        response = self.client.post("/texts", json={"text": source})
        path = f"/texts/{response.json()['id']}"
        self.worker.process_one_job()
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "failed")
        self.assertIn("Choose German", data["error_message"])
        self.assertEqual(data["source_text"], source)
        self.llm.extract_metadata.side_effect = None
        self.llm.extract_metadata.return_value = schemas.GeneratedMetadata(title="French", language="French", difficulty_level="A1")
        self.client.post(path+"/retry")
        self.worker.process_one_job()
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["language"], "French")

    def test_translation_retry_reuses_preparation_checkpoint(self) -> None:
        self.llm.translate_sentence_async.side_effect = RuntimeError("Provider unavailable")
        text_id = self._upload()
        path = f"/texts/{text_id}"
        before = self.client.get(path).json()["data"]
        self.llm.translate_sentence_async.side_effect = None
        self.client.post(path+"/retry")
        with mock.patch.object(self.preprocessing, "process_text", side_effect=AssertionError("Must not repeat NLP")) as prepare:
            self.assertTrue(self.worker.process_one_job())
            prepare.assert_not_called()
        after = self.client.get(path).json()["data"]
        self.assertEqual(after["status"], "processed")
        self.assertEqual([s["text"] for p in before["original_paragraphs"] for s in p["sentences"]],
                         [s["text"] for p in after["original_paragraphs"] for s in p["sentences"]])

    def test_http_intake_two_workers_and_active_retry_share_one_job(self) -> None:
        started, release = threading.Event(), threading.Event()

        async def translate(**kwargs):
            started.set()
            await asyncio.to_thread(release.wait, 10)
            return schemas.SentenceTranslation(translation="Saved translation", translation_hints=[])

        self.llm.translate_sentence_async.side_effect = translate
        response = self.client.post("/texts", json={"text": "Der Hund läuft.", "language": "German"})
        self.assertEqual(response.status_code, 200)
        text_id = response.json()["id"]
        self.llm.translate_sentence_async.assert_not_called()
        self.assertEqual(self.client.get(f"/texts/{text_id}").json()["data"]["status"], "processing")
        # Repeated pending retries reuse one durable record.
        self.assertEqual(self.client.post(f"/texts/{text_id}/retry").status_code, 200)
        thread = threading.Thread(target=self.worker.process_one_job)
        thread.start()
        try:
            self.assertTrue(started.wait(10))
            competitor = Worker(self.job_repo, app_state.text_service, worker_id="competitor")
            self.assertFalse(competitor.process_one_job())
            self.assertEqual(self.client.post(f"/texts/{text_id}/retry").status_code, 400)
            self.assertEqual(self.client.post(f"/texts/{text_id}/regenerate-words").status_code, 400)
        finally:
            release.set()
            thread.join(15)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.client.get(f"/texts/{text_id}").json()["data"]["status"], "processed")
        jobs = self.job_repo.load_jobs_by_text(text_id, "owner_local_default")
        self.assertEqual([(j.status, j.attempt_count) for j in jobs], [("completed", 1)])
        self.assertEqual(self.llm.translate_sentence_async.call_count, 1)
        self.assertEqual(self.llm.generate_practice_sentences_async.call_count, 1)

    def test_expired_inflight_worker_does_not_overwrite_replacement(self) -> None:
        started, release = threading.Event(), threading.Event()
        async def translate(**kwargs):
            if self.llm.translate_sentence_async.call_count == 1:
                started.set()
                await asyncio.to_thread(release.wait, 10)
                value = "Stale translation"
            else:
                value = "Replacement translation"
            return schemas.SentenceTranslation(translation=value, translation_hints=[])
        self.llm.translate_sentence_async.side_effect = translate
        response = self.client.post("/texts", json={"text": "Der Hund läuft.", "language": "German"})
        text_id = response.json()["id"]
        thread = threading.Thread(target=self.worker.process_one_job)
        thread.start()
        try:
            self.assertTrue(started.wait(10))
            jobs = self.job_repo.load_jobs_by_text(text_id, "owner_local_default")
            with sqlmodel.Session(self.engine) as session:
                row = session.get(BackgroundJobRecord, jobs[0].id)
                assert row is not None
                row.leased_until = utc_now() - timedelta(seconds=1)
                session.add(row)
                session.commit()
            # Even a replacement with the same configured worker ID has a unique lease token.
            replacement = Worker(self.job_repo, app_state.text_service, worker_id=self.worker.worker_id)
            self.assertTrue(replacement.process_one_job())
        finally:
            release.set()
            thread.join(15)
        self.assertFalse(thread.is_alive())
        data = self.client.get(f"/texts/{text_id}").json()["data"]
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["original_paragraphs"][0]["sentences"][0]["translation"], "Replacement translation")
        jobs = self.job_repo.load_jobs_by_text(text_id, "owner_local_default")
        self.assertEqual([(j.status, j.attempt_count) for j in jobs], [("completed", 2)])
        self.assertEqual(self.llm.generate_practice_sentences_async.call_count, 1)

    def test_embedded_worker_resumes_durable_queue_for_all_owners(self) -> None:
        response = self.client.post("/texts", json={"text": "Der Hund läuft.", "language": "German"}, headers={"X-Owner-Id": "other-owner"})
        self.assertEqual(response.status_code, 200)
        text_id = response.json()["id"]
        # Start a fresh API lifespan; recovery comes from the queue, not an owner-specific text scan.
        with testclient.TestClient(app.create_app(Settings(embedded_worker_enabled=True))) as client:
            jobs = self.job_repo.load_jobs_by_text(text_id, "other-owner")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                jobs = self.job_repo.load_jobs_by_text(text_id, "other-owner")
                if jobs[0].status == "completed":
                    break
                time.sleep(.02)
            self.assertEqual(jobs[0].status, "completed")
            self.assertEqual(client.get(f"/texts/{text_id}").status_code, 404)
        self.assertEqual(self.llm.translate_sentence_async.call_count, 1)

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
        self.worker.process_one_job()
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
        self.worker.process_one_job()
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
        self.llm.is_configured = False
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
        self.worker.process_one_job()

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
        self.worker.process_one_job()

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

    def test_missing_model_is_async_actionable_failure_with_source_saved(self) -> None:
        with mock.patch.object(preprocessing_service.spacy, "load", side_effect=OSError("missing")):
            response = self.client.post("/texts", json={"text": "Der Hund läuft.", "language": "German"})
            self.assertEqual(response.status_code, 200)
            self.worker.process_one_job()
        data = self.client.get(f"/texts/{response.json()['id']}").json()["data"]
        self.assertEqual(data["status"], "failed")
        self.assertIn("npm run bootstrap", data["error_message"])
        self.assertEqual(data["source_text"], "Der Hund läuft.")
        self.assertEqual(data["original_paragraphs"], [])
        # A later retry with the restored model prepares the original source.
        self.client.post(f"/texts/{response.json()['id']}/retry")
        self.worker.process_one_job()
        self.assertEqual(self.client.get(f"/texts/{response.json()['id']}").json()["data"]["status"], "processed")

    def test_regeneration_missing_model_preserves_original_and_saved_practice(self) -> None:
        text_id = self._upload()
        path = f"/texts/{text_id}"
        before = self.client.get(path).json()["data"]
        with mock.patch.object(self.preprocessing, "process_text", side_effect=preprocessing_service.MissingLanguageModelError("Run `npm run bootstrap`")):
            response = self.client.post(f"{path}/regenerate-words")
            self.assertEqual(response.status_code, 200)
            self.worker.process_one_job()
        data = self.client.get(path).json()["data"]
        self.assertEqual(data["status"], "failed")
        for key in ("original_paragraphs", "practice_sentences", "top_words", "source_text"):
            self.assertEqual(data[key], before[key])
        self.assertIn("npm run bootstrap", data["error_message"])


if __name__ == "__main__":
    unittest.main()
