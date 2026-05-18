"""JSON-backed repository for text records."""

import json
from pathlib import Path

from schemas.texts import TextData


class TextRepository:
    """Persist and retrieve text entries from a local JSON file."""

    def __init__(self, data_file: Path) -> None:
        """Initialize the repository with a path to the JSON database file."""

        self._data_file = data_file

    def load_all(self) -> list[TextData]:
        """Load and validate all stored text entries."""

        if not self._data_file.exists():
            return []

        content = self._data_file.read_text(encoding="utf-8")
        if not content.strip():
            return []

        loaded = json.loads(content)
        if isinstance(loaded, dict):
            return [TextData.model_validate(loaded)]
        if isinstance(loaded, list):
            return [TextData.model_validate(item) for item in loaded]
        raise ValueError("Database content must be a JSON list or object")

    def save_all(self, data: list[TextData]) -> None:
        """Write the full text collection to disk as JSON."""

        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump() for item in data]
        self._data_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
