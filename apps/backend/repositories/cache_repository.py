"""Repository for translation caching and token spend tracking."""

from datetime import datetime, time, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Engine, func
from sqlmodel import Session, select

from models.cache import TokenUsageRecord, TranslationCacheRecord, utc_now


class DailyBudgetExceededError(RuntimeError):
    """Raised when a user exceeds their daily LLM token allocation."""

    pass


class CacheRepository:
    """Manage cached translations and token spend audit logs."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_translation(
        self,
        source_language: str,
        target_language: str,
        sentence_hash: str,
        prompt_version: str = "v1",
    ) -> Optional[TranslationCacheRecord]:
        """Fetch cached translation by language pair, sentence hash, and prompt version."""
        with Session(self._engine) as session:
            statement = select(TranslationCacheRecord).where(
                TranslationCacheRecord.source_language == source_language,
                TranslationCacheRecord.target_language == target_language,
                TranslationCacheRecord.sentence_hash == sentence_hash,
                TranslationCacheRecord.prompt_version == prompt_version,
            )
            return session.exec(statement).first()

    def store_translation(
        self,
        source_language: str,
        target_language: str,
        sentence_hash: str,
        translation: str,
        translation_hints: Dict[str, Any] | list[Any],
        prompt_version: str = "v1",
    ) -> TranslationCacheRecord:
        """Persist a newly generated translation into the cache table."""
        with Session(self._engine) as session:
            try:
                record = TranslationCacheRecord(
                    source_language=source_language,
                    target_language=target_language,
                    sentence_hash=sentence_hash,
                    prompt_version=prompt_version,
                    translation=translation,
                    translation_hints=translation_hints if isinstance(translation_hints, dict) else {"hints": translation_hints},
                    created_at=utc_now(),
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
            except Exception:
                session.rollback()
                statement = select(TranslationCacheRecord).where(
                    TranslationCacheRecord.source_language == source_language,
                    TranslationCacheRecord.target_language == target_language,
                    TranslationCacheRecord.sentence_hash == sentence_hash,
                    TranslationCacheRecord.prompt_version == prompt_version,
                )
                existing = session.exec(statement).first()
                if existing:
                    return existing
                raise

    def record_usage(
        self,
        owner_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost_usd: float = 0.0,
    ) -> TokenUsageRecord:
        """Record token consumption for auditing and budget enforcement."""
        with Session(self._engine) as session:
            record = TokenUsageRecord(
                owner_id=owner_id,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost_usd,
                created_at=utc_now(),
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def get_daily_token_usage(
        self,
        owner_id: str,
        target_date: Optional[datetime] = None,
    ) -> int:
        """Calculate total tokens consumed by an owner during a single calendar day (UTC)."""
        dt = target_date or utc_now()
        start_of_day = datetime.combine(dt.date(), time.min, tzinfo=timezone.utc)
        end_of_day = datetime.combine(dt.date(), time.max, tzinfo=timezone.utc)

        with Session(self._engine) as session:
            statement = select(func.coalesce(func.sum(TokenUsageRecord.total_tokens), 0)).where(
                TokenUsageRecord.owner_id == owner_id,
                TokenUsageRecord.created_at >= start_of_day,
                TokenUsageRecord.created_at <= end_of_day,
            )
            result = session.exec(statement).first()
            return int(result or 0)

    def check_daily_budget(
        self,
        owner_id: str,
        daily_limit: int = 50_000,
    ) -> bool:
        """Check if an owner remains within their daily token spend allowance."""
        usage = self.get_daily_token_usage(owner_id)
        return usage < daily_limit
