"""Database-backed repository for text records."""

from typing import List, Optional, Tuple

from models.texts import (
    PracticeSentenceRecord,
    SentenceRecord,
    TextRecord,
    WordFrequencyRecord,
)
from sqlalchemy import Engine
from sqlmodel import Session, select


class TextRepository:
    """Persist and retrieve text entries using a relational database."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the repository with a SQLAlchemy database engine."""
        self._engine = engine

    def load_all_texts(self) -> List[TextRecord]:
        """Load all stored text entries."""
        with Session(self._engine) as session:
            statement = select(TextRecord).order_by(TextRecord.id)  # pyright: ignore
            return list(session.exec(statement).all())

    def load_one_text(self, text_id: int) -> Optional[TextRecord]:
        """Load a single text entry by database ID."""
        with Session(self._engine) as session:
            return session.get(TextRecord, text_id)

    def load_sentences(self, text_id: int) -> List[SentenceRecord]:
        """Load all sentences for a specific text, properly ordered."""
        with Session(self._engine) as session:
            statement = (
                select(SentenceRecord)
                .where(SentenceRecord.text_id == text_id)
                .order_by(SentenceRecord.paragraph_index, SentenceRecord.sentence_index)  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def load_practice_sentences(self, text_id: int) -> List[PracticeSentenceRecord]:
        """Load all practice sentences for a specific text."""
        with Session(self._engine) as session:
            statement = (
                select(PracticeSentenceRecord)
                .where(PracticeSentenceRecord.text_id == text_id)
                .order_by(PracticeSentenceRecord.sentence_index)  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def load_word_frequencies(self, text_id: int) -> List[WordFrequencyRecord]:
        """Load word frequencies for a specific text, sorted by highest count."""
        with Session(self._engine) as session:
            statement = (
                select(WordFrequencyRecord)
                .where(WordFrequencyRecord.text_id == text_id)
                .order_by(WordFrequencyRecord.count.desc())  # pyright: ignore
            )
            return list(session.exec(statement).all())

    def load_titles(self) -> List[Tuple[int, str]]:
        """Load ID and title of all texts for lightweight lists."""
        with Session(self._engine) as session:
            statement = select(TextRecord.id, TextRecord.title).order_by(TextRecord.id)  # pyright: ignore
            results = session.exec(statement).all()
            return [(row[0], row[1]) for row in results]  # pyright: ignore

    def save_text(self, record: TextRecord) -> TextRecord:
        """Write a new or updated text record to the database."""
        with Session(self._engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def update_text(self, record: TextRecord) -> TextRecord:
        """Update an existing text record in the database."""
        with Session(self._engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def update_sentence(self, record: SentenceRecord) -> SentenceRecord:
        """Update an existing sentence record in the database."""
        with Session(self._engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

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

    def delete_text(self, text_id: int) -> Optional[TextRecord]:
        """Delete one text entry from the database by ID (SQL cascades sentences)."""
        with Session(self._engine) as session:
            record = session.get(TextRecord, text_id)
            if record is not None:
                session.delete(record)
                session.commit()
            return record
