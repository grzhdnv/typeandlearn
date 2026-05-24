import sys
import unittest
from pathlib import Path
from sqlmodel import SQLModel, create_engine

# Add apps/backend to Python path so we can import modules directly
backend_dir = Path(__file__).resolve().parents[2] / "apps" / "backend"
sys.path.append(str(backend_dir))

# Import directly (not via apps.backend) to prevent double-importing in SQLModel metadata registry
from models.texts import TextRecord
from repositories.text_repository import TextRepository


class TextRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        """Set up an isolated in-memory SQLite database for each test."""
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)
        self.repository = TextRepository(self.engine)

    def tearDown(self) -> None:
        """Dispose of the database engine to close connections."""
        self.engine.dispose()

    def test_save_and_load_roundtrip(self) -> None:
        """Verify that records are successfully written to and read from the database."""
        record = TextRecord(
            title="Sample Text",
            original_paragraphs=[],
            practice_sentences=[],
        )

        saved = self.repository.save(record)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.title, "Sample Text")

        loaded = self.repository.load_all()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].title, "Sample Text")
        self.assertEqual(loaded[0].id, saved.id)

    def test_load_one(self) -> None:
        """Verify loading a single text record by its database ID."""
        record = TextRecord(
            title="Another Text",
            original_paragraphs=[],
            practice_sentences=[],
        )
        saved = self.repository.save(record)

        loaded = self.repository.load_one(saved.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Another Text")

        non_existent = self.repository.load_one(999)
        self.assertIsNone(non_existent)

    def test_load_titles(self) -> None:
        """Verify loading lightweight (id, title) tuples works correctly."""
        r1 = TextRecord(title="Text One", original_paragraphs=[], practice_sentences=[])
        r2 = TextRecord(title="Text Two", original_paragraphs=[], practice_sentences=[])
        self.repository.save(r1)
        self.repository.save(r2)

        titles = self.repository.load_titles()
        self.assertEqual(len(titles), 2)
        # Verify that titles match
        self.assertEqual(titles[0][1], "Text One")
        self.assertEqual(titles[1][1], "Text Two")

    def test_delete(self) -> None:
        """Verify deleting records by ID removes them from the database."""
        record = TextRecord(title="To Delete", original_paragraphs=[], practice_sentences=[])
        saved = self.repository.save(record)

        deleted = self.repository.delete(saved.id)
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted.title, "To Delete")

        loaded = self.repository.load_all()
        self.assertEqual(len(loaded), 0)

        # Deleting a non-existent ID should return None and not raise an error
        deleted_none = self.repository.delete(999)
        self.assertIsNone(deleted_none)


if __name__ == "__main__":
    unittest.main()
