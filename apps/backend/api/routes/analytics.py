"""API routes for practice sessions and learning analytics."""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, status

from app_state import analytics_service
from core.auth import get_current_owner_id
from schemas.analytics import (
    AnalyticsSummaryResponse,
    PracticeSessionCreate,
    PracticeSessionResponse,
    WeakWordResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/sessions",
    response_model=PracticeSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_session(
    payload: PracticeSessionCreate,
    owner_id: Annotated[str, Depends(get_current_owner_id)],
) -> PracticeSessionResponse:
    """Record metrics for a completed typing practice drill."""
    return analytics_service.record_session(owner_id, payload)


@router.get("/history", response_model=List[PracticeSessionResponse])
def get_session_history(
    owner_id: Annotated[str, Depends(get_current_owner_id)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> List[PracticeSessionResponse]:
    """Fetch paginated history of completed practice drills."""
    return analytics_service.get_recent_sessions(owner_id, limit=limit, offset=offset)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    owner_id: Annotated[str, Depends(get_current_owner_id)],
) -> AnalyticsSummaryResponse:
    """Fetch lifetime learning KPIs and recent progression trend."""
    return analytics_service.get_summary_stats(owner_id)


@router.get("/weak-words", response_model=List[WeakWordResponse])
def get_weak_words(
    owner_id: Annotated[str, Depends(get_current_owner_id)],
    language: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[WeakWordResponse]:
    """Fetch user's most frequently missed vocabulary words."""
    return analytics_service.get_weak_words(owner_id, language=language, limit=limit)
