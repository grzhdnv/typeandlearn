"""Tests for translation caching, token budgeting, and spend governance."""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import sqlmodel

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

with mock.patch.dict(os.environ, {
    "DEEPSEEK_API_KEY": "test-key",
    "DATABASE_URL": "sqlite://",
}):
    from models.cache import compute_sentence_hash
    from repositories.cache_repository import CacheRepository, DailyBudgetExceededError
    from repositories.job_repository import JobRepository
    from repositories.text_repository import TextRepository
    from schemas.texts import GeneratedMetadata, HintGroup, PracticeSentencesResponse, SentenceTranslation
    from services.dictionary_service import DictionaryService
    from services.llm_service import LlmService
    from services.preprocessing_service import PreprocessingService
    from services.text_service import TextService


class FakeUsage:
    """Mock token usage object mirroring Pydantic AI RunUsage."""

    def __init__(self, input_tokens: int = 120, output_tokens: int = 30) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens


class TranslationCacheTests(unittest.TestCase):
    """Verify sentence hash computation, cache repository, and budget enforcement."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = sqlmodel.create_engine(
            f"sqlite:///{directory}/test.sqlite",
            connect_args={"check_same_thread": False},
        )
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

        self.cache_repo = CacheRepository(self.engine)
        self.text_repo = TextRepository(self.engine)
        self.job_repo = JobRepository(self.engine)

        self.mock_llm = mock.Mock(spec=LlmService)
        self.mock_llm.model_name = "groq:llama-3.3-70b-versatile"
        self.mock_llm.structured_model_name = "groq:llama-3.3-70b-versatile"
        self.mock_llm.extract_metadata.return_value = GeneratedMetadata(
            title="Dog Story", difficulty_level="A1"
        )
        trans_res = SentenceTranslation(
            translation="The dog runs quickly.",
            translation_hints=[HintGroup(words=["Hund"], hint="dog")],
        )
        self.mock_llm.translate_sentence_async = mock.AsyncMock(
            return_value=(trans_res, FakeUsage(input_tokens=100, output_tokens=25))
        )

        practice_res = PracticeSentencesResponse(sentences=[])
        self.mock_llm.generate_practice_sentences_async = mock.AsyncMock(
            return_value=(practice_res, FakeUsage(input_tokens=80, output_tokens=20))
        )

        self.mock_dict = mock.Mock(spec=DictionaryService)
        self.mock_dict.translate_word.return_value = "dog"

        self.text_service = TextService(
            repository=self.text_repo,
            llm=self.mock_llm,
            preprocessing=PreprocessingService(),
            dictionary=self.mock_dict,
            job_repository=self.job_repo,
            cache_repository=self.cache_repo,
            daily_token_limit=50_000,
            prompt_version="v1",
        )

    def test_compute_sentence_hash_is_deterministic_and_normalized(self) -> None:
        """Hash generation handles whitespace and case variations consistently."""
        hash1 = compute_sentence_hash("  Der Hund läuft schnell.  ")
        hash2 = compute_sentence_hash("der hund läuft schnell.")
        hash3 = compute_sentence_hash("Der Hund schläft.")

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 64)

    def test_cache_repository_store_and_lookup(self) -> None:
        """Cache repository stores translations and retrieves by compound key."""
        s_hash = compute_sentence_hash("Das ist ein Test.")
        stored = self.cache_repo.store_translation(
            source_language="German",
            target_language="English",
            sentence_hash=s_hash,
            translation="This is a test.",
            translation_hints=[{"words": ["Test"], "hint": "test"}],
            prompt_version="v1",
        )

        self.assertIsNotNone(stored.id)
        self.assertEqual(stored.translation, "This is a test.")

        # Cache hit with exact key
        hit = self.cache_repo.get_translation(
            source_language="German",
            target_language="English",
            sentence_hash=s_hash,
            prompt_version="v1",
        )
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.translation, "This is a test.")

        # Cache miss with different prompt version
        miss_version = self.cache_repo.get_translation(
            source_language="German",
            target_language="English",
            sentence_hash=s_hash,
            prompt_version="v2",
        )
        self.assertIsNone(miss_version)

        # Cache miss with different language
        miss_lang = self.cache_repo.get_translation(
            source_language="Spanish",
            target_language="English",
            sentence_hash=s_hash,
            prompt_version="v1",
        )
        self.assertIsNone(miss_lang)

    def test_cache_repository_record_and_get_daily_token_usage(self) -> None:
        """Token usage records aggregate correctly by owner within the day."""
        owner = "user-123"
        other_owner = "user-456"

        self.cache_repo.record_usage(
            owner_id=owner,
            provider="groq",
            model="llama-3.3-70b-versatile",
            prompt_tokens=200,
            completion_tokens=50,
            total_tokens=250,
            estimated_cost_usd=0.00018,
        )
        self.cache_repo.record_usage(
            owner_id=owner,
            provider="groq",
            model="llama-3.3-70b-versatile",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.00010,
        )
        self.cache_repo.record_usage(
            owner_id=other_owner,
            provider="groq",
            model="llama-3.3-70b-versatile",
            prompt_tokens=500,
            completion_tokens=100,
            total_tokens=600,
            estimated_cost_usd=0.00045,
        )

        owner_total = self.cache_repo.get_daily_token_usage(owner)
        other_total = self.cache_repo.get_daily_token_usage(other_owner)

        self.assertEqual(owner_total, 400)
        self.assertEqual(other_total, 600)

        # Daily budget check
        self.assertTrue(self.cache_repo.check_daily_budget(owner, daily_limit=500))
        self.assertFalse(self.cache_repo.check_daily_budget(owner, daily_limit=400))
        self.assertFalse(self.cache_repo.check_daily_budget(owner, daily_limit=300))

    def test_text_service_cache_hit_bypasses_llm(self) -> None:
        """Sentences with existing cached translations do not invoke LLM."""
        owner_id = "user-cache-hit"
        sentence_text = "Der Hund läuft schnell."
        s_hash = compute_sentence_hash(sentence_text)

        # Pre-seed cache
        self.cache_repo.store_translation(
            source_language="German",
            target_language="English",
            sentence_hash=s_hash,
            translation="The cached dog runs swiftly.",
            translation_hints=[{"words": ["Hund"], "hint": "cached dog"}],
            prompt_version="v1",
        )

        # Upload text
        text_record = self.text_service.upload(
            text=sentence_text,
            language="German",
            owner_id=owner_id,
            title="Dog Story",
        )
        assert text_record.id is not None

        # Isolate translation caching: disable practice generation usage in this test
        self.mock_llm.generate_practice_sentences_async.return_value = (
            PracticeSentencesResponse(sentences=[]),
            None,
        )

        # Process text
        self.text_service.process_pending_text(text_record.id, owner_id)

        # Verification: LLM translation was NOT called
        self.mock_llm.translate_sentence_async.assert_not_called()

        # Sentence was populated from cache
        sentences = self.text_repo.load_sentences(text_record.id, owner_id)
        self.assertEqual(len(sentences), 1)
        self.assertEqual(sentences[0].translation, "The cached dog runs swiftly.")
        self.assertEqual(sentences[0].status, "processed")

        # Zero token usage recorded for owner
        self.assertEqual(self.cache_repo.get_daily_token_usage(owner_id), 0)

    def test_text_service_cache_miss_calls_llm_and_populates_cache(self) -> None:
        """Cache miss invokes LLM, populates cache table, and logs token usage."""
        owner_id = "user-cache-miss"
        sentence_text = "Der Hund läuft schnell."
        s_hash = compute_sentence_hash(sentence_text)

        # Verify initial cache miss
        cached_before = self.cache_repo.get_translation(
            "German", "English", s_hash, "v1"
        )
        self.assertIsNone(cached_before)

        # Upload & process text
        text_record = self.text_service.upload(
            text=sentence_text,
            language="German",
            owner_id=owner_id,
            title="New Dog Story",
        )
        assert text_record.id is not None
        self.text_service.process_pending_text(text_record.id, owner_id)

        # LLM was invoked
        self.mock_llm.translate_sentence_async.assert_called_once()

        # Cache is now populated
        cached_after = self.cache_repo.get_translation(
            "German", "English", s_hash, "v1"
        )
        self.assertIsNotNone(cached_after)
        assert cached_after is not None
        self.assertEqual(cached_after.translation, "The dog runs quickly.")

        # Token usage was recorded (125 translation + 100 practice = 225)
        daily_usage = self.cache_repo.get_daily_token_usage(owner_id)
        self.assertEqual(daily_usage, 225)

    def test_daily_budget_exceeded_blocks_llm_invocation(self) -> None:
        """When daily token spend is exceeded, DailyBudgetExceededError is raised."""
        owner_id = "user-over-budget"

        # Configure small budget
        service = TextService(
            repository=self.text_repo,
            llm=self.mock_llm,
            preprocessing=PreprocessingService(),
            dictionary=self.mock_dict,
            job_repository=self.job_repo,
            cache_repository=self.cache_repo,
            daily_token_limit=100,
            prompt_version="v1",
        )

        # Exhaust budget
        self.cache_repo.record_usage(
            owner_id=owner_id,
            provider="groq",
            model="llama-3.3-70b-versatile",
            prompt_tokens=80,
            completion_tokens=30,
            total_tokens=110,
        )

        text_record = service.upload(
            text="Ein neuer deutscher Satz zum Übersetzen.",
            language="German",
            owner_id=owner_id,
            title="Over Budget Text",
        )
        assert text_record.id is not None

        # Processing should raise DailyBudgetExceededError
        with self.assertRaises(DailyBudgetExceededError):
            service.process_pending_text(text_record.id, owner_id)

        # LLM was never called
        self.mock_llm.translate_sentence_async.assert_not_called()
