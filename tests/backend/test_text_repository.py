import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from apps.backend.repositories.text_repository import TextRepository
from apps.backend.schemas.texts import TextData


class TextRepositoryTests(unittest.TestCase):
    def test_load_and_save_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "db.json"
            repository = TextRepository(db_path)
            payload = [
                TextData(
                    title="Sample",
                    original_paragraphs=[],
                    practice_sentences=[],
                )
            ]

            repository.save_all(payload)
            loaded = repository.load_all()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].title, "Sample")

    def test_load_single_object_legacy_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "db.json"
            db_path.write_text(
                json.dumps(
                    {
                        "title": "Legacy",
                        "original_paragraphs": [],
                        "practice_sentences": [],
                    }
                ),
                encoding="utf-8",
            )

            repository = TextRepository(db_path)
            loaded = repository.load_all()
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].title, "Legacy")


if __name__ == "__main__":
    unittest.main()
