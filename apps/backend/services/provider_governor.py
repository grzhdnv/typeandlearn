"""Transactional quota and spend reservations; never stores learning content."""

from __future__ import annotations

import math
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable
from uuid import uuid4

from sqlalchemy import Engine, func, text
from sqlmodel import Session, select

from core.settings import Settings
from models.cache import TokenUsageRecord
from models.providers import ProviderCallRecord, ProviderGateRecord


class QuotaUnavailable(RuntimeError):
    def __init__(self, wait_seconds: float):
        super().__init__("Provider allowance temporarily exhausted")
        self.wait_seconds = max(0.05, wait_seconds)


class ProviderBudgetExceeded(RuntimeError):
    pass


def duration_seconds(value: str) -> float:
    try:
        return max(0, float(value))
    except ValueError:
        parts = re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h|d)", value)
        return sum(float(number) * {"ms": .001, "s": 1, "m": 60, "h": 3600, "d": 86400}[unit] for number, unit in parts)


class ProviderGovernor:
    def __init__(self, engine: Engine, settings: Settings, clock: Callable[[], float] = time.time):
        self.engine = engine
        self.settings = settings
        self.clock = clock

    def _lock(self, session: Session) -> None:
        if self.engine.dialect.name == "sqlite":
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        elif self.engine.dialect.name == "postgresql":
            session.execute(text("SELECT pg_advisory_xact_lock(76239402)"))
        else:
            raise ValueError("Provider reservations require SQLite or PostgreSQL")

    @staticmethod
    def _totals(session: Session, provider: str, since: float) -> tuple[int, int, int]:
        result = session.exec(select(
            func.count(), func.coalesce(func.sum(ProviderCallRecord.tokens), 0),
            func.coalesce(func.sum(ProviderCallRecord.cost_microusd), 0),
        ).where(ProviderCallRecord.provider == provider, ProviderCallRecord.created_at >= since)).one()
        return int(result[0]), int(result[1]), int(result[2])

    def _cost(self, provider: str, inputs: int, outputs: int, cached: int = 0) -> int:
        if provider != "deepseek":
            return 0  # This application's Groq account uses its free allowance.
        cfg = self.settings
        cached = min(max(cached, 0), inputs)
        return math.ceil((inputs - cached) * cfg.deepseek_input_usd_per_mtok
                         + cached * cfg.deepseek_cached_input_usd_per_mtok
                         + outputs * cfg.deepseek_output_usd_per_mtok)

    def reserve(self, provider: str, model: str, owner: str, task: str,
                input_bound: int, token_estimate: int, max_output: int) -> str:
        now = self.clock()
        today = datetime.fromtimestamp(now, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        day_start = today.timestamp()
        month_start = today.replace(day=1).timestamp()
        reservation_tokens = (input_bound if provider == "deepseek" else token_estimate) + max_output
        cost_bound = self._cost(provider, input_bound, max_output)
        with Session(self.engine) as session:
            self._lock(session)
            gate = session.get(ProviderGateRecord, provider) or ProviderGateRecord(provider=provider)
            if now < gate.cooldown_until:
                raise QuotaUnavailable(gate.cooldown_until - now)
            if now >= gate.tokens_reset_at:
                gate.tokens_remaining = None
            if now >= gate.requests_reset_at:
                gate.requests_remaining = None

            if provider == "groq":
                minute_requests, minute_tokens, _ = self._totals(session, provider, now - 60)
                daily_requests, daily_tokens, _ = self._totals(session, provider, day_start)
                cfg = self.settings
                if daily_requests >= cfg.groq_rpd or daily_tokens + reservation_tokens > cfg.groq_tpd:
                    raise QuotaUnavailable(day_start + 86400 - now)
                if minute_requests >= cfg.groq_rpm or minute_tokens + reservation_tokens > cfg.groq_tpm:
                    raise QuotaUnavailable(1)  # In-flight reservations may reconcile before the window resets.
                if gate.requests_remaining is not None and gate.requests_remaining <= 0:
                    raise QuotaUnavailable(gate.requests_reset_at - now)
                if gate.tokens_remaining is not None and reservation_tokens > gate.tokens_remaining:
                    raise QuotaUnavailable(gate.tokens_reset_at - now)
                if gate.tokens_remaining is not None:
                    gate.tokens_remaining -= reservation_tokens
                if gate.requests_remaining is not None:
                    gate.requests_remaining -= 1
            else:
                daily_cost = self._totals(session, provider, day_start)[2]
                monthly_cost = self._totals(session, provider, month_start)[2]
                if (daily_cost + cost_bound > round(self.settings.deepseek_daily_usd * 1_000_000)
                        or monthly_cost + cost_bound > round(self.settings.deepseek_monthly_usd * 1_000_000)):
                    raise ProviderBudgetExceeded("DeepSeek daily or monthly fallback budget exhausted")

            pending = session.exec(select(func.coalesce(func.sum(ProviderCallRecord.tokens), 0)).where(
                ProviderCallRecord.owner_id == owner,
                ProviderCallRecord.created_at >= day_start,
                ProviderCallRecord.status.in_(["reserved", "unknown"]),  # pyright: ignore[reportAttributeAccessIssue]
            )).one()
            used = session.exec(select(func.coalesce(func.sum(TokenUsageRecord.total_tokens), 0)).where(
                TokenUsageRecord.owner_id == owner, TokenUsageRecord.created_at >= today,
            )).one()
            if int(pending) + int(used) + reservation_tokens > self.settings.daily_token_limit:
                raise ProviderBudgetExceeded("Daily application token budget exhausted")

            call_id = uuid4().hex
            session.add(gate)
            session.add(ProviderCallRecord(id=call_id, provider=provider, model=model,
                        owner_id=owner, task=task, created_at=now, tokens=reservation_tokens,
                        cost_microusd=cost_bound))
            session.commit()
            return call_id

    def finish(self, call_id: str, status_code: int | None, body: dict | None = None,
               headers: dict[str, str] | None = None) -> None:
        now = self.clock()
        body = body or {}
        headers = headers or {}
        with Session(self.engine) as session:
            self._lock(session)
            call = session.get(ProviderCallRecord, call_id)
            if call is None or call.status != "reserved":
                return
            reserved_tokens = call.tokens
            call.status_code = status_code
            usage = body.get("usage")
            if isinstance(usage, dict) and "prompt_tokens" in usage and "completion_tokens" in usage:
                inputs, outputs = max(0, int(usage["prompt_tokens"])), max(0, int(usage["completion_tokens"]))
                details = usage.get("prompt_tokens_details") or {}
                cached = int(usage.get("prompt_cache_hit_tokens") or details.get("cached_tokens") or 0)
                call.tokens = max(0, inputs + outputs - (cached if call.provider == "groq" else 0))
                call.cost_microusd = self._cost(call.provider, inputs, outputs, cached)
                call.response_model = str(body.get("model") or call.model)
                call.status = "succeeded" if status_code is not None and status_code < 400 else "failed"
                session.add(TokenUsageRecord(
                    owner_id=call.owner_id, provider=call.provider, model=call.response_model,
                    prompt_tokens=inputs, completion_tokens=outputs, total_tokens=inputs + outputs,
                    estimated_cost_usd=call.cost_microusd / 1_000_000,
                    created_at=datetime.fromtimestamp(now, timezone.utc),
                ))
            elif status_code in (400, 401, 402, 403, 404, 413, 422, 429):
                call.tokens, call.cost_microusd, call.status = 0, 0, "failed"
            else:
                # Keep the reservation if billing is unknown (timeout/crash/missing usage).
                call.status = "unknown"

            gate = session.get(ProviderGateRecord, call.provider) or ProviderGateRecord(provider=call.provider)
            if call.provider == "groq":
                if gate.tokens_remaining is not None:
                    gate.tokens_remaining += reserved_tokens - call.tokens
                for kind in ("tokens", "requests"):
                    remaining = headers.get(f"x-ratelimit-remaining-{kind}")
                    reset = headers.get(f"x-ratelimit-reset-{kind}")
                    if remaining is not None and reset:
                        current = getattr(gate, f"{kind}_remaining")
                        reset_at = getattr(gate, f"{kind}_reset_at")
                        try:
                            value = int(remaining)
                        except ValueError:
                            continue  # A malformed optional header must not lose usage accounting.
                        setattr(gate, f"{kind}_remaining", min(current, value) if current is not None and now < reset_at else value)
                        setattr(gate, f"{kind}_reset_at", now + duration_seconds(reset))
            if status_code == 429:
                retry = headers.get("retry-after", "1")
                try:
                    delay = float(retry)
                except ValueError:
                    try:
                        delay = parsedate_to_datetime(retry).timestamp() - now
                    except (ValueError, TypeError):
                        delay = 1
                gate.cooldown_until = max(gate.cooldown_until, now + max(1, delay))
            elif status_code in (500, 502, 503, 504):
                gate.cooldown_until = max(gate.cooldown_until, now + 5)
            session.add(gate)
            session.add(call)
            session.commit()
