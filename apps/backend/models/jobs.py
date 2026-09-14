"""Database model for background job tracking and transactional leasing."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from models.cache import utc_now


class BackgroundJobRecord(SQLModel, table=True):
    """Database record representing a durable background job."""

    __tablename__ = "background_jobs"  # pyright: ignore[reportAssignmentType]

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    text_id: Optional[int] = Field(
        default=None,
        foreign_key="texts.id",
        index=True,
        ondelete="CASCADE",
    )
    task_type: str = Field(index=True)  # e.g. "process_text"
    status: str = Field(
        default="pending",
        index=True,
    )  # "pending", "leased", "completed", "failed", "dead_letter"
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    attempt_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    leased_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    worker_id: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
