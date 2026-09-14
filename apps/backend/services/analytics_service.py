"""Service layer for learning analytics, session recording, and progress trends."""

from typing import List, Optional

from repositories.analytics_repository import AnalyticsRepository
from repositories.text_repository import TextRepository
from schemas.analytics import (
    AnalyticsSummaryResponse,
    PracticeSessionCreate,
    PracticeSessionResponse,
    WeakWordResponse,
)


class AnalyticsService:
    """Orchestrates recording and reporting of typing practice analytics."""

    def __init__(
        self,
        analytics_repo: AnalyticsRepository,
        text_repo: TextRepository,
    ) -> None:
        self._analytics_repo = analytics_repo
        self._text_repo = text_repo

    def record_session(
        self,
        owner_id: str,
        create_data: PracticeSessionCreate,
    ) -> PracticeSessionResponse:
        """Record completed sentence drill metrics and update persistent weak words."""
        language = "Unknown"
        text_record = self._text_repo.load_one_text(create_data.text_id, owner_id)
        if text_record and text_record.language:
            language = text_record.language

        record = self._analytics_repo.record_session(
            owner_id=owner_id,
            create_data=create_data,
            language=language,
        )

        return PracticeSessionResponse(
            id=record.id or 0,
            owner_id=record.owner_id,
            text_id=record.text_id,
            sentence_index=record.sentence_index,
            sentence_text=record.sentence_text,
            target_type=record.target_type,
            net_wpm=record.net_wpm,
            raw_wpm=record.raw_wpm,
            accuracy=record.accuracy,
            active_seconds=record.active_seconds,
            mistake_count=record.mistake_count,
            mistakes_detail=record.mistakes_detail,
            completed_at=record.completed_at,
        )

    def get_recent_sessions(
        self,
        owner_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PracticeSessionResponse]:
        """Fetch chronological list of recent practice sessions."""
        records = self._analytics_repo.get_recent_sessions(
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        )
        return [
            PracticeSessionResponse(
                id=r.id or 0,
                owner_id=r.owner_id,
                text_id=r.text_id,
                sentence_index=r.sentence_index,
                sentence_text=r.sentence_text,
                target_type=r.target_type,
                net_wpm=r.net_wpm,
                raw_wpm=r.raw_wpm,
                accuracy=r.accuracy,
                active_seconds=r.active_seconds,
                mistake_count=r.mistake_count,
                mistakes_detail=r.mistakes_detail,
                completed_at=r.completed_at,
            )
            for r in records
        ]

    def get_summary_stats(self, owner_id: str) -> AnalyticsSummaryResponse:
        """Fetch summary KPIs and recent trend line."""
        return self._analytics_repo.get_summary_stats(owner_id)

    def get_weak_words(
        self,
        owner_id: str,
        language: Optional[str] = None,
        limit: int = 20,
    ) -> List[WeakWordResponse]:
        """Fetch top weak vocabulary words."""
        records = self._analytics_repo.get_weak_words(
            owner_id=owner_id,
            language=language,
            limit=limit,
        )
        return [
            WeakWordResponse(
                id=r.id or 0,
                owner_id=r.owner_id,
                language=r.language,
                word=r.word,
                mistake_count=r.mistake_count,
                practice_count=r.practice_count,
                last_mistake_at=r.last_mistake_at,
            )
            for r in records
        ]
