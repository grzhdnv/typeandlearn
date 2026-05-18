"""Domain service for text retrieval, upload, and deletion workflows."""

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

        return self._repository.load_all()

    def get_titles(self) -> list[TextTitle]:
        """Return index-based title metadata for text selection."""

        items = self._repository.load_all()
        return [TextTitle(id=f"{i:02d}", title=item.title) for i, item in enumerate(items)]

    def get_one(self, text_id: str) -> TextData:
        """Return one text entry by index encoded as string."""

        index = int(text_id)
        items = self._repository.load_all()
        if index < 0 or index >= len(items):
            raise IndexError("Text not found")
        return items[index]

    def upload(self, text: str) -> None:
        """Generate and persist a new text entry from raw input."""

        new_entry = self._llm.text_to_db(text)
        items = self._repository.load_all()
        items.append(new_entry)
        self._repository.save_all(items)

    def delete(self, text_id: str) -> TextData:
        """Delete and return one text entry by index."""

        index = int(text_id)
        items = self._repository.load_all()
        if index < 0 or index >= len(items):
            raise IndexError("Text not found")
        deleted = items.pop(index)
        self._repository.save_all(items)
        return deleted
