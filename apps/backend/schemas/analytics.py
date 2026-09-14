"""Pydantic schemas for practice sessions and learning analytics."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PracticeSessionCreate(BaseModel):
    """Payload to record a completed practice session drill."""

    text_id: int
    sentence_index: int = Field(default=0)
    sentence_text: str = Field(default="")
    target_type: str = Field(default="original")
    net_wpm: float = Field(default=0.0)
    raw_wpm: float = Field(default=0.0)
    accuracy: float = Field(default=0.0)
    active_seconds: float = Field(default=0.0)
    mistake_count: int = Field(default=0)
    mistakes_detail: Optional[List[Dict[str, Any]]] = None
    mistaken_words: Optional[List[str]] = None


class PracticeSessionResponse(BaseModel):
    """Full database representation of a recorded practice session."""

    id: int
    owner_id: str
    text_id: int
    sentence_index: int
    sentence_text: str
    target_type: str
    net_wpm: float
    raw_wpm: float
    accuracy: float
    active_seconds: float
    mistake_count: int
    mistakes_detail: Optional[List[Dict[str, Any]]] = None
    completed_at: datetime


class WeakWordResponse(BaseModel):
    """Aggregate mistake frequency statistics for a specific vocabulary item."""

    id: int
    owner_id: str
    language: str
    word: str
    mistake_count: int
    practice_count: int
    last_mistake_at: datetime


class SessionTrendPoint(BaseModel):
    """Point in time trend tracking for WPM and accuracy."""

    session_id: int
    completed_at: datetime
    net_wpm: float
    accuracy: float


class AnalyticsSummaryResponse(BaseModel):
    """Aggregate KPIs and recent progression metrics for a user."""

    total_drills: int
    total_practice_seconds: float
    avg_net_wpm: float
    peak_net_wpm: float
    avg_accuracy: float
    total_mistakes: int
    recent_trend: List[SessionTrendPoint]
