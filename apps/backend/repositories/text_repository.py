"""Database-backed repository for text records."""

from typing import Any, Dict, List, Optional

from core.metadata import normalize_optional_metadata

from models.analytics import PracticeSessionRecord
from models.jobs import BackgroundJobRecord, utc_now
from models.texts import (
    PracticeSentenceRecord,
    SentenceRecord,
    TextRecord,
    WordFrequencyRecord,
)
from sqlalchemy import Engine, delete, text
from sqlmodel import Session, col, select


class TextRepository:
    """Persist and retrieve text entries using a relational database with owner scoping."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the repository with a SQLAlchemy database engine."""
        self._engine = engine

    def load_all_texts(self, owner_id: str) -> List[TextRecord]:
        """Load all stored text entries for an owner."""
        with Session(self._engine) as session:
            statement = (
                select(TextRecord)
                .where(TextRecord.owner_id == owner_id)
                .order_by(TextRecord.id)  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def load_one_text(self, text_id: int, owner_id: str) -> Optional[TextRecord]:
        """Load a single text entry by database ID and owner ID."""
        with Session(self._engine) as session:
            statement = select(TextRecord).where(
                TextRecord.id == text_id,
                TextRecord.owner_id == owner_id,
            )
            return session.exec(statement).first()

    def load_sentences(self, text_id: int, owner_id: str) -> List[SentenceRecord]:
        """Load all sentences for a specific text and owner, properly ordered."""
        with Session(self._engine) as session:
            statement = (
                select(SentenceRecord)
                .where(
                    SentenceRecord.text_id == text_id,
                    SentenceRecord.owner_id == owner_id,
                )
                .order_by(SentenceRecord.paragraph_index, SentenceRecord.sentence_index)  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def load_practice_sentences(self, text_id: int, owner_id: str) -> List[PracticeSentenceRecord]:
        """Load all practice sentences for a specific text and owner."""
        with Session(self._engine) as session:
            statement = (
                select(PracticeSentenceRecord)
                .where(
                    PracticeSentenceRecord.text_id == text_id,
                    PracticeSentenceRecord.owner_id == owner_id,
                )
                .order_by(PracticeSentenceRecord.sentence_index)  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def load_word_frequencies(self, text_id: int, owner_id: str) -> List[WordFrequencyRecord]:
        """Load word frequencies for a specific text and owner, sorted by highest count."""
        with Session(self._engine) as session:
            statement = (
                select(WordFrequencyRecord)
                .where(
                    WordFrequencyRecord.text_id == text_id,
                    WordFrequencyRecord.owner_id == owner_id,
                )
                .order_by(WordFrequencyRecord.count.desc())  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def load_titles(self, owner_id: str) -> List[TextRecord]:
        """Load metadata for all texts of an owner for lightweight lists."""
        with Session(self._engine) as session:
            statement = (
                select(TextRecord)
                .where(TextRecord.owner_id == owner_id)
                .order_by(TextRecord.id)  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def save_text(self, record: TextRecord) -> TextRecord:
        """Write a new or updated text record to the database."""
        with Session(self._engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def save_text_with_job(
        self,
        record: TextRecord,
        task_type: str,
        payload: Dict[str, Any],
        sentences: List[SentenceRecord],
        frequencies: List[WordFrequencyRecord],
    ) -> tuple[TextRecord, BackgroundJobRecord]:
        """Atomically persist a text record, its initial sentences, frequencies, and a background job in a single transaction."""
        with Session(self._engine) as session:
            session.add(record)
            session.flush()
            assert record.id is not None

            for s in sentences:
                s.text_id = record.id
                session.add(s)

            for f in frequencies:
                f.text_id = record.id
                session.add(f)

            job = BackgroundJobRecord(
                owner_id=record.owner_id,
                text_id=record.id,
                task_type=task_type,
                payload=payload,
                status="pending",
                attempt_count=0,
                max_retries=3,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(job)
            session.commit()
            session.refresh(record)
            session.refresh(job)
            return record, job

    def queue_enrichment(
        self,
        text_id: int,
        owner_id: str,
        *,
        frequencies: Optional[List[WordFrequencyRecord]] = None,
        filtering_method: Optional[str] = None,
    ) -> None:
        """Commit a text reset and its queue entry together; never duplicate live work."""
        with Session(self._engine) as session:
            if self._engine.dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            elif self._engine.dialect.name == "postgresql":
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:text_id)"), {"text_id": text_id}
                )
            record = session.exec(
                select(TextRecord)
                .where(
                    TextRecord.id == text_id,
                    TextRecord.owner_id == owner_id,
                )
                .with_for_update()
            ).first()
            if record is None:
                raise IndexError("Text not found")
            jobs = session.exec(
                select(BackgroundJobRecord)
                .where(
                    BackgroundJobRecord.owner_id == owner_id,
                    BackgroundJobRecord.text_id == text_id,
                    BackgroundJobRecord.task_type == "process_text",
                    BackgroundJobRecord.status.in_(["pending", "leased"]),  # pyright: ignore
                )
                .with_for_update()
            ).all()
            if any(job.status == "leased" for job in jobs):
                raise ValueError("Enrichment is already running; wait for it to finish")
            if frequencies is not None:
                session.exec(
                    delete(WordFrequencyRecord).where(
                        col(WordFrequencyRecord.owner_id) == owner_id,
                        col(WordFrequencyRecord.text_id) == text_id,
                    )
                )
                session.add_all(frequencies)
            if filtering_method is not None:
                options: Dict[str, Any] = dict(
                    record.intake_options or {"prepared": True, "metadata_done": True}
                )
                options.update(
                    filtering_method=filtering_method,
                    words_pending=True,
                    strict_filtering=filtering_method == "llm",
                )
                record.intake_options = options
            record.status = "processing"
            record.enrichment_stage = "queued"
            record.error_message = None
            session.add(record)
            if jobs:
                # A manual retry can wake the existing backoff, but keeps its budget.
                for job in jobs:
                    job.leased_until = None
                    session.add(job)
            else:
                session.add(
                    BackgroundJobRecord(
                        owner_id=owner_id,
                        text_id=text_id,
                        task_type="process_text",
                        payload={"text_id": text_id},
                    )
                )
            session.commit()

    def update_progress(
        self, text_id: int, owner_id: str, sentence_index: Optional[int] = None
    ) -> TextRecord:
        """Update only progress, without overwriting concurrent preparation or metadata."""
        with Session(self._engine) as session:
            if self._engine.dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            record = session.exec(
                select(TextRecord)
                .where(
                    TextRecord.id == text_id,
                    TextRecord.owner_id == owner_id,
                )
                .with_for_update()
            ).first()
            if record is None:
                raise IndexError("Text not found")
            indices = set(record.completed_sentence_indices or [])
            if sentence_index is None:
                indices.clear()
            elif sentence_index < 0 or sentence_index >= record.total_sentences:
                raise ValueError("Sentence index is outside the original text")
            else:
                indices.add(sentence_index)
            record.completed_sentence_indices = sorted(indices)
            record.completed_sentences = len(indices)
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def update_processing_state(
        self,
        text_id: int,
        owner_id: str,
        status: str,
        stage: str,
        error: Optional[str] = None,
    ) -> TextRecord:
        with Session(self._engine) as session:
            record = session.exec(
                select(TextRecord)
                .where(
                    TextRecord.id == text_id,
                    TextRecord.owner_id == owner_id,
                )
                .with_for_update()
            ).one()
            record.status, record.enrichment_stage, record.error_message = (
                status,
                stage,
                error,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def apply_metadata(
        self, text_id: int, owner_id: str, values: Dict[str, Any], *, inferred: bool = False
    ) -> TextRecord:
        with Session(self._engine) as session:
            if self._engine.dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            record = session.exec(
                select(TextRecord)
                .where(
                    TextRecord.id == text_id,
                    TextRecord.owner_id == owner_id,
                )
                .with_for_update()
            ).one()
            defaults = {
                "title": "[Untitled]",
                "language": "Unknown",
                "difficulty_level": "Unrated",
                "author": None,
                "category": None,
            }
            options = dict(record.intake_options or {})
            missing = options.get("missing_metadata", [])
            for name in defaults:
                if name not in values:
                    continue
                value = values[name]
                current = getattr(record, name)
                if name in {"author", "category"}:
                    value = normalize_optional_metadata(value)
                    current = normalize_optional_metadata(current)
                elif value is None:
                    continue
                if not inferred or (name in missing and current == defaults[name]):
                    setattr(record, name, value)
            if inferred:
                options["metadata_done"] = True
                record.intake_options = options
            else:
                # Even explicit edits matching a placeholder must beat inference.
                options["missing_metadata"] = [
                    name for name in missing if name not in values
                ]
                if record.intake_options is not None:
                    record.intake_options = options
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def save_preparation(
        self,
        text_id: int,
        owner_id: str,
        language: str,
        frequencies: List[WordFrequencyRecord],
        *,
        sentences: Optional[List[SentenceRecord]] = None,
        words_pending: bool = False,
    ) -> TextRecord:
        """Commit sentence boundaries and vocabulary checkpoints without replacing progress."""
        with Session(self._engine) as session:
            if self._engine.dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            record = session.exec(
                select(TextRecord)
                .where(
                    TextRecord.id == text_id,
                    TextRecord.owner_id == owner_id,
                )
                .with_for_update()
            ).one()
            if record.language != language:
                raise ValueError("Language changed during preparation; retry enrichment")
            options = dict(record.intake_options or {})
            if sentences is not None:
                if options.get("prepared"):
                    return record
                session.add_all(sentences)
                record.total_sentences = len(sentences)
                record.word_count = sum(
                    len(sentence.original_text.split()) for sentence in sentences
                )
                record.estimated_time_minutes = max(1, record.word_count // 40)
                options["prepared"] = True
            session.exec(
                delete(WordFrequencyRecord).where(
                    col(WordFrequencyRecord.owner_id) == owner_id,
                    col(WordFrequencyRecord.text_id) == text_id,
                )
            )
            session.add_all(frequencies)
            options["words_pending"] = words_pending
            record.intake_options = options
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def update_text(self, record: TextRecord) -> TextRecord:
        """Update an existing text record in the database."""
        with Session(self._engine) as session:
            merged_record = session.merge(record)
            session.commit()
            session.refresh(merged_record)
            return merged_record

    def update_sentence(self, record: SentenceRecord) -> SentenceRecord:
        """Update an existing sentence record in the database."""
        with Session(self._engine) as session:
            merged_record = session.merge(record)
            session.commit()
            session.refresh(merged_record)
            return merged_record

    def update_word_frequency(self, record: WordFrequencyRecord) -> WordFrequencyRecord:
        """Update an existing word frequency record in the database."""
        with Session(self._engine) as session:
            merged_record = session.merge(record)
            session.commit()
            session.refresh(merged_record)
            return merged_record

    def save_sentences(self, sentences: List[SentenceRecord]) -> None:
        """Bulk save sentences to the database."""
        with Session(self._engine) as session:
            session.add_all(sentences)
            session.commit()

    def save_practice_sentences(self, sentences: List[PracticeSentenceRecord]) -> None:
        """Bulk save practice sentences to the database."""
        with Session(self._engine) as session:
            session.add_all(sentences)
            session.commit()

    def save_word_frequencies(self, frequencies: List[WordFrequencyRecord]) -> None:
        """Bulk save word frequencies to the database."""
        with Session(self._engine) as session:
            session.add_all(frequencies)
            session.commit()

    def delete_word_frequencies(self, text_id: int, owner_id: str) -> None:
        """Delete all word frequencies for a specific text and owner."""
        with Session(self._engine) as session:
            statement = select(WordFrequencyRecord).where(
                WordFrequencyRecord.text_id == text_id,
                WordFrequencyRecord.owner_id == owner_id,
            )  # pyright: ignore
            records = session.exec(statement).all()
            for record in records:
                session.delete(record)
            session.commit()

    def delete_practice_sentences(self, text_id: int, owner_id: str) -> None:
        """Delete all practice sentences for a specific text and owner."""
        with Session(self._engine) as session:
            statement = select(PracticeSentenceRecord).where(
                PracticeSentenceRecord.text_id == text_id,
                PracticeSentenceRecord.owner_id == owner_id,
            )  # pyright: ignore
            records = session.exec(statement).all()
            for record in records:
                session.delete(record)
            session.commit()

    def delete_text(self, text_id: int, owner_id: str) -> Optional[TextRecord]:
        """Delete one text entry and its dependent records by ID and owner ID."""
        with Session(self._engine) as session:
            record = self.load_one_text(text_id, owner_id)
            if record is not None:
                for table in (
                    SentenceRecord,
                    PracticeSentenceRecord,
                    WordFrequencyRecord,
                    PracticeSessionRecord,
                    BackgroundJobRecord,
                ):
                    session.exec(delete(table).where(col(table.text_id) == text_id, col(table.owner_id) == owner_id))
                session.delete(record)
                session.commit()
            return record
