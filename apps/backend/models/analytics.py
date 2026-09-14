"""Database models for practice sessions and learning analytics."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from models.cache import utc_now


class PracticeSessionRecord(SQLModel, table=True):
    """Database record for an individual completed typing practice session."""

    __tablename__ = "practice_sessions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        Index("ix_practice_sessions_owner_completed", "owner_id", "completed_at"),
        Index("ix_practice_sessions_owner_text", "owner_id", "text_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    text_id: int = Field(foreign_key="texts.id", index=True, ondelete="CASCADE")
    sentence_index: int = Field(default=0)
    sentence_text: str = Field(default="")
    target_type: str = Field(default="original")  # "original" | "generated"
    net_wpm: float = Field(default=0.0)
    raw_wpm: float = Field(default=0.0)
    accuracy: float = Field(default=0.0)
    active_seconds: float = Field(default=0.0)
    mistake_count: int = Field(default=0)
    mistakes_detail: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    completed_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )


class WeakWordRecord(SQLModel, table=True):
    """Database record aggregating persistent lexical mistakes per user."""

    __tablename__ = "weak_words"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "language",
            "word",
            name="uq_weak_words_owner_lang_word",
        ),
        Index("ix_weak_words_owner_mistakes", "owner_id", "mistake_count"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    language: str = Field(default="Unknown", index=True)
    word: str = Field(index=True)
    mistake_count: int = Field(default=0)
    practice_count: int = Field(default=0)
    last_mistake_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
