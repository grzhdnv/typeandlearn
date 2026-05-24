"""Database-backed repository for text records."""

from typing import List, Optional, Tuple

from models.texts import TextRecord
from sqlalchemy import Engine
from sqlmodel import Session, select


class TextRepository:
    """Persist and retrieve text entries using a relational database (SQLite/PostgreSQL)."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the repository with a SQLAlchemy database engine."""
        self._engine = engine

    def load_all(self) -> List[TextRecord]:
        """Load all stored text entries."""
        with Session(self._engine) as session:
            statement = select(TextRecord).order_by(TextRecord.id)  # pyright: ignore[reportArgumentType]
            return list(session.exec(statement).all())

    def load_one(self, text_id: int) -> Optional[TextRecord]:
        """Load a single text entry by database ID."""
        with Session(self._engine) as session:
            return session.get(TextRecord, text_id)

    def load_titles(self) -> List[Tuple[int, str]]:
        """Load ID and title of all texts for lightweight lists."""
        with Session(self._engine) as session:
            statement = select(TextRecord.id, TextRecord.title).order_by(TextRecord.id)  # pyright: ignore[reportArgumentType]
            results = session.exec(statement).all()
            # SQLModel returns list of tuple-like rows
            return [(row[0], row[1]) for row in results]  # pyright: ignore[reportReturnType]

    def save(self, record: TextRecord) -> TextRecord:
        """Write a new or updated text record to the database."""
        with Session(self._engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def delete(self, text_id: int) -> Optional[TextRecord]:
        """Delete one text entry from the database by ID."""
        with Session(self._engine) as session:
            record = session.get(TextRecord, text_id)
            if record is not None:
                session.delete(record)
                session.commit()
            return record
