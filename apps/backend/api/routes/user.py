"""API routes for user profile management, data export, and GDPR/CCPA erasure."""

import json
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete
from sqlmodel import Session, col, select

from core.auth import get_current_owner_id
from core.database import engine
from models.analytics import PracticeSessionRecord, WeakWordRecord, utc_now
from models.cache import TokenUsageRecord
from models.jobs import BackgroundJobRecord
from models.texts import (
    PracticeSentenceRecord,
    SentenceRecord,
    TextRecord,
    WordFrequencyRecord,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/export")
def export_user_data(
    owner_id: Annotated[str, Depends(get_current_owner_id)],
) -> Response:
    """Generate a machine-readable JSON archive of all data owned by the caller (GDPR Article 20)."""
    with Session(engine) as session:
        texts = list(session.exec(select(TextRecord).where(col(TextRecord.owner_id) == owner_id)).all())
        sentences = list(session.exec(select(SentenceRecord).where(col(SentenceRecord.owner_id) == owner_id)).all())
        practice_sentences = list(session.exec(select(PracticeSentenceRecord).where(col(PracticeSentenceRecord.owner_id) == owner_id)).all())
        word_frequencies = list(session.exec(select(WordFrequencyRecord).where(col(WordFrequencyRecord.owner_id) == owner_id)).all())
        practice_sessions = list(session.exec(select(PracticeSessionRecord).where(col(PracticeSessionRecord.owner_id) == owner_id)).all())
        weak_words = list(session.exec(select(WeakWordRecord).where(col(WeakWordRecord.owner_id) == owner_id)).all())
        token_usage = list(session.exec(select(TokenUsageRecord).where(col(TokenUsageRecord.owner_id) == owner_id)).all())

    export_payload: Dict[str, Any] = {
        "export_metadata": {
            "owner_id": owner_id,
            "exported_at": utc_now().isoformat(),
            "format_version": "1.0",
            "entity_counts": {
                "texts": len(texts),
                "sentences": len(sentences),
                "practice_sentences": len(practice_sentences),
                "word_frequencies": len(word_frequencies),
                "practice_sessions": len(practice_sessions),
                "weak_words": len(weak_words),
                "token_usage_records": len(token_usage),
            },
        },
        "texts": [t.model_dump() for t in texts],
        "sentences": [s.model_dump() for s in sentences],
        "practice_sentences": [ps.model_dump() for ps in practice_sentences],
        "word_frequencies": [wf.model_dump() for wf in word_frequencies],
        "practice_sessions": [
            {**rec.model_dump(), "completed_at": rec.completed_at.isoformat()}
            for rec in practice_sessions
        ],
        "weak_words": [
            {**w.model_dump(), "last_mistake_at": w.last_mistake_at.isoformat()}
            for w in weak_words
        ],
        "token_usage_records": [
            {**tu.model_dump(), "created_at": tu.created_at.isoformat()}
            for tu in token_usage
        ],
    }

    content = json.dumps(export_payload, indent=2)
    filename = f"typeandlearn-export-{owner_id}.json"

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete("/account", status_code=status.HTTP_200_OK)
def delete_user_account(
    owner_id: Annotated[str, Depends(get_current_owner_id)],
) -> Dict[str, Any]:
    """Permanently purge all user data, texts, and learning analytics (GDPR Article 17 / CCPA)."""
    with Session(engine) as session:
        # Cascade-delete all records belonging to owner
        session.exec(delete(WeakWordRecord).where(col(WeakWordRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.exec(delete(PracticeSessionRecord).where(col(PracticeSessionRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.exec(delete(TokenUsageRecord).where(col(TokenUsageRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.exec(delete(BackgroundJobRecord).where(col(BackgroundJobRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.exec(delete(SentenceRecord).where(col(SentenceRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.exec(delete(PracticeSentenceRecord).where(col(PracticeSentenceRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.exec(delete(WordFrequencyRecord).where(col(WordFrequencyRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.exec(delete(TextRecord).where(col(TextRecord.owner_id) == owner_id))  # pyright: ignore[reportCallIssue]
        session.commit()

    return {
        "status": "deleted",
        "owner_id": owner_id,
        "deleted_at": utc_now().isoformat(),
    }
