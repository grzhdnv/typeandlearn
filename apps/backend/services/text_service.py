"""Domain service for text retrieval, upload, and deletion workflows."""

from models.texts import TextRecord
from repositories.text_repository import TextRepository
from schemas.texts import TextData, TextTitle
from services.llm_service import LlmService


class TextService:
    """Coordinate repository persistence with LLM-backed processing."""

    def __init__(self, repository: TextRepository, llm: LlmService) -> None:
        """Bind storage and generation dependencies."""

        self._repository = repository
        self._llm = llm

    def get_all(self) -> list[TextData]:
        """Return all stored text entries."""

        records = self._repository.load_all()
        return [
            TextData(
                id=record.id,
                title=record.title,
                original_paragraphs=record.original_paragraphs,
                practice_sentences=record.practice_sentences,
            )
            for record in records
        ]

    def get_titles(self) -> list[TextTitle]:
        """Return database-backed title metadata for text selection."""

        titles = self._repository.load_titles()
        # Convert integer ID to string representation for contract compatibility
        return [TextTitle(id=str(tid), title=title) for tid, title in titles]

    def get_one(self, text_id: str) -> TextData:
        """Return one text entry by its database ID."""

        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.load_one(tid)
        if record is None:
            raise IndexError("Text not found")

        return TextData(
            id=record.id,
            title=record.title,
            original_paragraphs=record.original_paragraphs,
            practice_sentences=record.practice_sentences,
        )

    def upload(self, text: str) -> TextRecord:
        """Generate and persist a new text entry from raw input."""

        new_entry = self._llm.text_to_db(text)
        record = TextRecord(
            title=new_entry.title,
            original_paragraphs=new_entry.original_paragraphs,
            practice_sentences=new_entry.practice_sentences,
        )
        return self._repository.save(record)

    def delete(self, text_id: str) -> TextData:
        """Delete and return one text entry by its database ID."""

        try:
            tid = int(text_id)
        except ValueError as error:
            raise ValueError(f"Invalid text ID format: {text_id}") from error

        record = self._repository.delete(tid)
        if record is None:
            raise IndexError("Text not found")

        return TextData(
            id=record.id,
            title=record.title,
            original_paragraphs=record.original_paragraphs,
            practice_sentences=record.practice_sentences,
        )
