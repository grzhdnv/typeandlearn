"""Database models for translation caching and token usage tracking."""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def compute_sentence_hash(sentence: str) -> str:
    """Generate deterministic sha256 hash from trimmed, lowercased sentence."""
    normalized = sentence.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class TranslationCacheRecord(SQLModel, table=True):
    """Cached sentence translation to avoid redundant LLM billing and latency."""

    __tablename__ = "translation_cache"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "source_language",
            "target_language",
            "sentence_hash",
            "prompt_version",
            name="uq_translation_cache_key",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    source_language: str = Field(index=True)
    target_language: str = Field(default="English", index=True)
    sentence_hash: str = Field(index=True)
    prompt_version: str = Field(default="v1", index=True)
    translation: str
    translation_hints: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class TokenUsageRecord(SQLModel, table=True):
    """Audit log of LLM token consumption for daily budget governance."""

    __tablename__ = "token_usage_records"  # pyright: ignore[reportAssignmentType]

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    provider: str = Field(index=True)  # "groq", "deepseek"
    model: str = Field(index=True)
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    estimated_cost_usd: float = Field(default=0.0)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
