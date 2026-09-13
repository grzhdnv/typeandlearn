"""Database-backed repository for text records."""

from typing import Any, Dict, List, Optional

from models.jobs import BackgroundJobRecord, utc_now
from models.texts import (
    PracticeSentenceRecord,
    SentenceRecord,
    TextRecord,
    WordFrequencyRecord,
)
from sqlalchemy import Engine
from sqlmodel import Session, select


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
        """Delete one text entry from the database by ID and owner ID (SQL cascades sentences)."""
        with Session(self._engine) as session:
            record = self.load_one_text(text_id, owner_id)
            if record is not None:
                session.delete(record)
                session.commit()
            return record
