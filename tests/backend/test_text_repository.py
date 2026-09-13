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
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}
        )
        SQLModel.metadata.create_all(self.engine)
        self.repository = TextRepository(self.engine)
        self.owner = "user_alpha"
        self.other_owner = "user_beta"

    def tearDown(self) -> None:
        """Dispose of the database engine to close connections."""
        self.engine.dispose()

    def test_save_and_load_roundtrip(self) -> None:
        """Verify that records are successfully written to and read from the database."""
        record = TextRecord(
            owner_id=self.owner,
            title="Sample Text",
        )

        saved = self.repository.save_text(record)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.title, "Sample Text")
        self.assertEqual(saved.owner_id, self.owner)

        loaded = self.repository.load_all_texts(self.owner)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].title, "Sample Text")
        self.assertEqual(loaded[0].id, saved.id)

    def test_load_one(self) -> None:
        """Verify loading a single text record by its database ID and owner."""
        record = TextRecord(
            owner_id=self.owner,
            title="Another Text",
        )
        saved = self.repository.save_text(record)
        assert saved.id is not None

        loaded = self.repository.load_one_text(saved.id, self.owner)
        assert loaded is not None
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Another Text")

        # Wrong owner cannot access
        wrong_owner_loaded = self.repository.load_one_text(saved.id, self.other_owner)
        self.assertIsNone(wrong_owner_loaded)

        non_existent = self.repository.load_one_text(999, self.owner)
        self.assertIsNone(non_existent)

    def test_load_titles(self) -> None:
        """Verify loading lightweight metadata works correctly and scopes by owner."""
        r1 = TextRecord(owner_id=self.owner, title="Text One")
        r2 = TextRecord(owner_id=self.owner, title="Text Two")
        r_other = TextRecord(owner_id=self.other_owner, title="Other Text")
        self.repository.save_text(r1)
        self.repository.save_text(r2)
        self.repository.save_text(r_other)

        titles = self.repository.load_titles(self.owner)
        self.assertEqual(len(titles), 2)
        self.assertEqual(titles[0].title, "Text One")
        self.assertEqual(titles[1].title, "Text Two")

        other_titles = self.repository.load_titles(self.other_owner)
        self.assertEqual(len(other_titles), 1)
        self.assertEqual(other_titles[0].title, "Other Text")

    def test_delete(self) -> None:
        """Verify deleting records by ID and owner removes them cleanly."""
        record = TextRecord(owner_id=self.owner, title="To Delete")
        saved = self.repository.save_text(record)
        assert saved.id is not None

        # Other owner attempting delete returns None and does not delete
        cross_deleted = self.repository.delete_text(saved.id, self.other_owner)
        self.assertIsNone(cross_deleted)
        self.assertEqual(len(self.repository.load_all_texts(self.owner)), 1)

        deleted = self.repository.delete_text(saved.id, self.owner)
        assert deleted is not None
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted.title, "To Delete")

        loaded = self.repository.load_all_texts(self.owner)
        self.assertEqual(len(loaded), 0)

        # Deleting a non-existent ID should return None and not raise an error
        deleted_none = self.repository.delete_text(999, self.owner)
        self.assertIsNone(deleted_none)


if __name__ == "__main__":
    unittest.main()
