"""Database models for structured text records."""

from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class TextRecord(SQLModel, table=True):
    """Database record representation of a text unit."""

    __tablename__ = "texts"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    status: str = Field(default="pending", index=True)


class SentenceRecord(SQLModel, table=True):
    """Database record representation of an individual sentence."""

    __tablename__ = "sentences"

    id: Optional[int] = Field(default=None, primary_key=True)
    text_id: int = Field(foreign_key="texts.id", index=True, ondelete="CASCADE")
    paragraph_index: int
    sentence_index: int
    original_text: str
    translation: Optional[str] = None
    translation_hints: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    status: str = Field(default="pending", index=True)


class WordFrequencyRecord(SQLModel, table=True):
    """Word frequency counts extracted during preprocessing."""

    __tablename__ = "word_frequencies"

    id: Optional[int] = Field(default=None, primary_key=True)
    text_id: int = Field(foreign_key="texts.id", index=True, ondelete="CASCADE")
    word: str = Field(index=True)
    count: int = Field(default=1)


class PracticeSentenceRecord(SQLModel, table=True):
    """Generated practice sentences based on word frequencies."""

    __tablename__ = "practice_sentences"

    id: Optional[int] = Field(default=None, primary_key=True)
    text_id: int = Field(foreign_key="texts.id", index=True, ondelete="CASCADE")
    sentence_index: int
    sentence: str
    translation: str
    translation_hints: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
