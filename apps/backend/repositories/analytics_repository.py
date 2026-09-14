"""Repository for practice session metrics and learning analytics."""

from typing import List, Optional

from sqlalchemy import Engine, func
from sqlmodel import Session, col, select

from models.analytics import PracticeSessionRecord, WeakWordRecord, utc_now
from schemas.analytics import (
    AnalyticsSummaryResponse,
    PracticeSessionCreate,
    SessionTrendPoint,
)


class AnalyticsRepository:
    """Manage practice sessions, weak word tracking, and user learning metrics."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record_session(
        self,
        owner_id: str,
        create_data: PracticeSessionCreate,
        language: str = "Unknown",
    ) -> PracticeSessionRecord:
        """Atomically persist a drill completion session and update weak words."""
        with Session(self._engine) as session:
            record = PracticeSessionRecord(
                owner_id=owner_id,
                text_id=create_data.text_id,
                sentence_index=create_data.sentence_index,
                sentence_text=create_data.sentence_text,
                target_type=create_data.target_type,
                net_wpm=round(create_data.net_wpm, 1),
                raw_wpm=round(create_data.raw_wpm, 1),
                accuracy=round(create_data.accuracy, 1),
                active_seconds=round(create_data.active_seconds, 2),
                mistake_count=create_data.mistake_count,
                mistakes_detail=create_data.mistakes_detail or [],
                completed_at=utc_now(),
            )
            session.add(record)

            # Update weak words if errors were tracked
            if create_data.mistaken_words:
                for raw_word in create_data.mistaken_words:
                    clean_word = raw_word.strip()
                    if not clean_word:
                        continue
                    stmt = select(WeakWordRecord).where(
                        WeakWordRecord.owner_id == owner_id,
                        WeakWordRecord.language == language,
                        WeakWordRecord.word == clean_word,
                    )
                    existing = session.exec(stmt).first()
                    if existing:
                        existing.mistake_count += 1
                        existing.practice_count += 1
                        existing.last_mistake_at = utc_now()
                        session.add(existing)
                    else:
                        new_weak = WeakWordRecord(
                            owner_id=owner_id,
                            language=language,
                            word=clean_word,
                            mistake_count=1,
                            practice_count=1,
                            last_mistake_at=utc_now(),
                        )
                        session.add(new_weak)

            session.commit()
            session.refresh(record)
            return record

    def get_recent_sessions(
        self,
        owner_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PracticeSessionRecord]:
        """Fetch recent completed sessions for an owner ordered by completion time descending."""
        with Session(self._engine) as session:
            statement = (
                select(PracticeSessionRecord)
                .where(PracticeSessionRecord.owner_id == owner_id)
                .order_by(PracticeSessionRecord.completed_at.desc())  # pyright: ignore[reportAttributeAccessIssue]
                .offset(offset)
                .limit(limit)
            )
            return list(session.exec(statement).all())

    def get_summary_stats(self, owner_id: str) -> AnalyticsSummaryResponse:
        """Compute aggregate lifetime KPIs and recent progression trend points."""
        with Session(self._engine) as session:
            count_stmt = select(  # pyright: ignore[reportCallIssue]
                func.count(col(PracticeSessionRecord.id)),
                func.coalesce(func.sum(col(PracticeSessionRecord.active_seconds)), 0.0),
                func.coalesce(func.avg(col(PracticeSessionRecord.net_wpm)), 0.0),
                func.coalesce(func.max(col(PracticeSessionRecord.net_wpm)), 0.0),
                func.coalesce(func.avg(col(PracticeSessionRecord.accuracy)), 0.0),
                func.coalesce(func.sum(col(PracticeSessionRecord.mistake_count)), 0),
            ).where(PracticeSessionRecord.owner_id == owner_id)

            row = session.exec(count_stmt).one()
            total_drills = int(row[0])
            total_time = float(row[1])
            avg_wpm = round(float(row[2]), 1)
            peak_wpm = round(float(row[3]), 1)
            avg_accuracy = round(float(row[4]), 1)
            total_mistakes = int(row[5])

            # Query recent 20 drills for progression curve (chronological order)
            trend_stmt = (
                select(PracticeSessionRecord)
                .where(PracticeSessionRecord.owner_id == owner_id)
                .order_by(PracticeSessionRecord.completed_at.desc())  # pyright: ignore[reportAttributeAccessIssue]
                .limit(20)
            )
            recent_drills = list(session.exec(trend_stmt).all())
            recent_drills.reverse()  # Chronological order

            trend_points = [
                SessionTrendPoint(
                    session_id=d.id or 0,
                    completed_at=d.completed_at,
                    net_wpm=d.net_wpm,
                    accuracy=d.accuracy,
                )
                for d in recent_drills
            ]

            return AnalyticsSummaryResponse(
                total_drills=total_drills,
                total_practice_seconds=round(total_time, 1),
                avg_net_wpm=avg_wpm,
                peak_net_wpm=peak_wpm,
                avg_accuracy=avg_accuracy,
                total_mistakes=total_mistakes,
                recent_trend=trend_points,
            )

    def get_weak_words(
        self,
        owner_id: str,
        language: Optional[str] = None,
        limit: int = 20,
    ) -> List[WeakWordRecord]:
        """Fetch top weak vocabulary words by mistake count."""
        with Session(self._engine) as session:
            stmt = select(WeakWordRecord).where(WeakWordRecord.owner_id == owner_id)
            if language:
                stmt = stmt.where(WeakWordRecord.language == language)
            stmt = stmt.order_by(WeakWordRecord.mistake_count.desc()).limit(limit)  # pyright: ignore[reportAttributeAccessIssue]
            return list(session.exec(stmt).all())
