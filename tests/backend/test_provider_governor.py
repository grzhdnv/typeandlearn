"""Atomic provider quotas, actual usage, and paid reservation limits."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pathlib
import sys
import tempfile
import unittest

import sqlmodel
from sqlmodel import Session, select

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from core.settings import Settings
from models.cache import TokenUsageRecord
from models.providers import ProviderCallRecord
from services.provider_governor import ProviderBudgetExceeded, ProviderGovernor, QuotaUnavailable, duration_seconds


class ProviderGovernorTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.url = f"sqlite:///{folder}/quota.sqlite"
        self.engine = sqlmodel.create_engine(self.url, connect_args={"check_same_thread": False})
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.now = datetime(2026, 10, 20, 1, tzinfo=timezone.utc).timestamp()
        self.cfg = Settings(daily_token_limit=1_000_000, groq_rpm=24, groq_tpm=6400)
        self.gov = ProviderGovernor(self.engine, self.cfg, lambda: self.now)

    def reserve(self, provider="groq", governor=None, owner="reader", inputs=100, outputs=100):
        return (governor or self.gov).reserve(provider, "test-model", owner, "translation", inputs, inputs, outputs)

    def test_separate_connections_cannot_race_past_the_request_limit(self):
        self.cfg.groq_rpm = 2
        other_engine = sqlmodel.create_engine(self.url, connect_args={"check_same_thread": False})
        self.addCleanup(other_engine.dispose)
        other = ProviderGovernor(other_engine, self.cfg, lambda: self.now)
        def attempt(index):
            try:
                self.reserve(governor=self.gov if index % 2 else other, owner=f"reader-{index}")
                return True
            except QuotaUnavailable:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt, range(8))), 2)

    def test_actual_usage_releases_unused_token_reservations(self):
        self.cfg.groq_tpm = 300
        request_id = self.reserve()
        with self.assertRaises(QuotaUnavailable):
            self.reserve()
        self.gov.finish(request_id, 200, {"model": "actual", "usage": {"prompt_tokens": 20, "completion_tokens": 10}})
        self.reserve()

    def test_header_token_reset_and_retry_after_are_shared(self):
        call = self.reserve()
        self.gov.finish(call, 200, {"usage": {"prompt_tokens": 10, "completion_tokens": 10}},
                        {"x-ratelimit-remaining-tokens": "5", "x-ratelimit-reset-tokens": "2m"})
        with self.assertRaises(QuotaUnavailable) as error:
            self.reserve()
        self.assertEqual(error.exception.wait_seconds, 120)
        self.now += 121
        call = self.reserve()
        self.gov.finish(call, 429, {}, {"retry-after": "90"})
        with self.assertRaises(QuotaUnavailable) as error:
            self.reserve()
        self.assertEqual(error.exception.wait_seconds, 90)
        self.assertEqual(duration_seconds("1h2m3.5s"), 3723.5)
        self.assertEqual(duration_seconds("250ms"), .25)

    def test_daily_allowance_is_not_a_per_owner_limit(self):
        self.cfg.groq_rpd = 1
        self.reserve(owner="first")
        self.now += 61
        with self.assertRaises(QuotaUnavailable):
            self.reserve(owner="second")
        self.now += 86400
        self.reserve(owner="second")

    def test_deepseek_caps_include_pending_requests_and_unknown_billing(self):
        self.cfg.deepseek_daily_usd = .00015
        call = self.reserve("deepseek")
        with self.assertRaises(ProviderBudgetExceeded):
            self.reserve("deepseek", owner="another")
        self.gov.finish(call, None)
        with self.assertRaises(ProviderBudgetExceeded):
            self.reserve("deepseek")

    def test_monthly_cap_survives_day_rollover(self):
        self.cfg.deepseek_monthly_usd = .00015
        self.reserve("deepseek")
        self.now += 86400
        with self.assertRaises(ProviderBudgetExceeded):
            self.reserve("deepseek")
        self.now = datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp()
        self.reserve("deepseek")

    def test_actual_model_cache_discount_and_idempotent_accounting(self):
        call = self.reserve("deepseek")
        result = {"model": "deepseek-actual", "usage": {"prompt_tokens": 100, "completion_tokens": 10, "prompt_cache_hit_tokens": 80}}
        self.gov.finish(call, 200, result)
        self.gov.finish(call, 200, result)
        with Session(self.engine) as session:
            usage = session.exec(select(TokenUsageRecord)).all()
            self.assertEqual(len(usage), 1)
            self.assertEqual(usage[0].model, "deepseek-actual")
            self.assertEqual(usage[0].estimated_cost_usd, .000019)
            record = session.get(ProviderCallRecord, call)
            assert record is not None
            self.assertEqual(record.cost_microusd, 19)

    def test_per_user_token_budget_includes_outstanding_calls(self):
        self.cfg.daily_token_limit = 300
        self.reserve()
        with self.assertRaises(ProviderBudgetExceeded):
            self.reserve("deepseek")

    def test_nonbillable_failures_release_paid_reservations(self):
        self.cfg.deepseek_daily_usd = .00015
        call = self.reserve("deepseek")
        self.gov.finish(call, 401)
        self.reserve("deepseek")

    def test_malformed_optional_header_does_not_discard_known_usage(self):
        call = self.reserve()
        self.gov.finish(call, 200, {"usage": {"prompt_tokens": 10, "completion_tokens": 5}},
                        {"x-ratelimit-remaining-tokens": "invalid", "x-ratelimit-reset-tokens": "1m"})
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(TokenUsageRecord)).one().total_tokens, 15)

    def test_openrouter_separate_daily_and_minute_quota_and_reset(self):
        self.cfg.openrouter_rpm = 1
        self.cfg.openrouter_rpd = 2
        self.cfg.deepseek_daily_usd = self.cfg.deepseek_monthly_usd = 0
        def reserve():
            return self.gov.reserve("openrouter", "test/model:free", "reader", "translation", 100, 100, 100)
        call = reserve()
        with self.assertRaises(QuotaUnavailable):
            reserve()
        self.gov.finish(call, 429, {}, {"x-ratelimit-reset": str((self.now + 90) * 1000)})
        self.now += 61
        with self.assertRaises(QuotaUnavailable) as error:
            reserve()
        self.assertEqual(error.exception.wait_seconds, 29)
        self.now += 30
        reserve()
        self.now += 61
        with self.assertRaises(QuotaUnavailable):
            reserve()
        self.now += 86400
        reserve()
        self.reserve("groq")

    def test_unknown_provider_cannot_bypass_policy(self):
        with self.assertRaises(ValueError):
            self.reserve("unknown")
        with self.assertRaises(ValueError):
            self.reserve("openrouter")
