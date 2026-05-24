"""Database models for structured text records."""

from typing import List, Optional, Type, TypeVar
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import JSON, TypeDecorator
from sqlmodel import Column, Field, SQLModel

from schemas.texts import Paragraph, PracticeSentence

T = TypeVar("T", bound=BaseModel)


class PydanticListType(TypeDecorator):
    """Custom SQLAlchemy type decorator to store a list of Pydantic models in a JSON column."""

    impl = JSON
    cache_ok = True

    def __init__(self, model_class: Type[T]) -> None:
        """Initialize the custom type with the specific Pydantic model class."""
        super().__init__()
        self.model_class = model_class
        self.adapter = TypeAdapter(List[model_class])

    def process_bind_param(self, value, dialect):
        """Serialize a list of Pydantic models to a list of dicts (JSON-serializable)."""
        if value is None:
            return None
        # Coerce/validate the input list to ensure they are actual Pydantic model instances
        validated = self.adapter.validate_python(value)
        return self.adapter.dump_python(validated, mode="json")

    def process_result_value(self, value, dialect):
        """Deserialize a list of dicts from the database back to Pydantic models."""
        if value is None:
            return None
        # Convert JSON structure back to Pydantic objects
        return self.adapter.validate_python(value)


class TextRecord(SQLModel, table=True):
    """Database record representation of a text unit."""

    __tablename__ = "texts"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    original_paragraphs: List[Paragraph] = Field(
        default_factory=list,
        sa_column=Column(PydanticListType(Paragraph)),
    )
    practice_sentences: List[PracticeSentence] = Field(
        default_factory=list,
        sa_column=Column(PydanticListType(PracticeSentence)),
    )
