"""Synthetic evaluation resumes preserve evidence and stop on local budget errors."""

import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import sqlmodel
from pydantic_ai.exceptions import ModelHTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps/backend"))

from scripts import evaluate_providers as evaluation
from schemas.texts import GeneratedMetadata, PracticeSentencesResponse, SentenceTranslation


class ProviderEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.output = Path(self.directory) / "result.json"
        self.engine = sqlmodel.create_engine(f"sqlite:///{self.directory}/ledger.sqlite")
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.enterContext(mock.patch.object(evaluation, "engine", self.engine))
        self.enterContext(mock.patch.object(evaluation, "init_db"))
        self.calls = []
        calls = self.calls

        class FakeService:
            is_configured = True

            def __init__(self, *args, **kwargs):
                self.transport = kwargs["transport"]

            async def aclose(self):
                await self.transport.aclose()

            async def translate_sentence_async(self, *args, **kwargs):
                calls.append(("translation", kwargs["source_language"]))
                return SentenceTranslation(translation="Synthetic", translation_hints=[])

            def extract_metadata(self, *args):
                calls.append(("metadata", "French"))
                return GeneratedMetadata(title="Synthetic", difficulty_level="B1", language="French")

            async def generate_practice_sentences_async(self, *args, **kwargs):
                calls.append(("practice", kwargs["source_language"]))
                return PracticeSentencesResponse(sentences=[])

        self.fake = FakeService
        self.enterContext(mock.patch.object(evaluation, "LlmService", FakeService))

    def test_resume_keeps_success_and_retains_prior_failure(self):
        success = {"model": "groq:test", "task": "translation", "language": "German", "output": {"translation": "Prior"}}
        failure = {"model": "groq:test", "task": "translation", "language": "French", "error": "Prior failure"}
        self.output.write_text(json.dumps([success, failure]))
        asyncio.run(evaluation.evaluate(["groq:test"], self.output, resume=True))
        rows = json.loads(self.output.read_text())
        self.assertEqual(len(rows), 7)
        self.assertEqual(len(self.calls), 6)
        self.assertNotIn(("translation", "German"), self.calls)
        self.assertEqual(rows[0], success)
        self.assertEqual(rows[1]["previous_attempts"], [failure])

    def test_local_402_stops_without_a_provider_ledger_row(self):
        async def blocked(*args, **kwargs):
            self.calls.append(("blocked", "German"))
            raise ModelHTTPError(402, "test", {"message": "Daily application token budget exhausted"})
        with mock.patch.object(self.fake, "translate_sentence_async", blocked):
            with self.assertRaisesRegex(RuntimeError, "Evaluation stopped"):
                asyncio.run(evaluation.evaluate(["groq:test"], self.output))
        rows = json.loads(self.output.read_text())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["calls"], [])
        self.assertEqual(len(self.calls), 1)
