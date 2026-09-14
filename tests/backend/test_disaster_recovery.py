"""Unit and integration tests for automated backup, restore, and disaster recovery rehearsal."""

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.append(str(Path(__file__).resolve().parents[2] / "apps/backend"))
sys.path.append(str(Path(__file__).resolve().parents[2] / "scripts"))

from backup import create_backup
from restore import perform_restore
from sqlmodel import SQLModel, Session, create_engine, select

from models.analytics import PracticeSessionRecord, WeakWordRecord
from models.cache import TokenUsageRecord
from models.texts import SentenceRecord, TextRecord


class TestDisasterRecovery(unittest.TestCase):
    """Test suite for backup snapshotting, checksum validation, and disaster recovery rehearsal."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.db_path = self.base_path / "live_rehearsal.db"
        self.backup_dir = self.base_path / "backups"
        self.db_url = f"sqlite:///{self.db_path}"

        # Initialize test database
        self.engine = create_engine(self.db_url)
        SQLModel.metadata.create_all(self.engine)

        # Seed realistic tenant data
        with Session(self.engine) as session:
            text = TextRecord(
                title="Disaster Recovery Seed Story",
                language="German",
                difficulty_level="B1",
                owner_id="owner_dr_test",
                word_count=50,
                completed_sentences=1,
                total_sentences=2,
            )
            session.add(text)
            session.commit()
            session.refresh(text)
            assert text.id is not None
            text_id = text.id

            sentence = SentenceRecord(
                owner_id="owner_dr_test",
                text_id=text_id,
                paragraph_index=0,
                sentence_index=0,
                original_text="Der Wiederherstellungstest ist erfolgreich.",
                translation="The recovery test is successful.",
            )
            session.add(sentence)

            practice = PracticeSessionRecord(
                owner_id="owner_dr_test",
                text_id=text_id,
                sentence_index=0,
                sentence_text="Der Wiederherstellungstest ist erfolgreich.",
                target_type="original",
                net_wpm=72.5,
                raw_wpm=74.0,
                accuracy=98.0,
                active_seconds=5.2,
                mistake_count=0,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(practice)

            weak_word = WeakWordRecord(
                owner_id="owner_dr_test",
                language="German",
                word="Wiederherstellungstest",
                mistake_count=1,
                practice_count=3,
                last_mistake_at=datetime.now(timezone.utc),
            )
            session.add(weak_word)

            usage = TokenUsageRecord(
                owner_id="owner_dr_test",
                provider="groq",
                model="llama-3.3-70b-versatile",
                prompt_tokens=85,
                completion_tokens=22,
                total_tokens=107,
                estimated_cost_usd=0.00008,
            )
            session.add(usage)
            session.commit()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_backup_and_restore_full_fidelity(self):
        """Disaster recovery rehearsal restores 100% of data after catastrophic loss."""
        # 1. Create automated backup
        backup_report = create_backup(
            output_dir=self.backup_dir,
            database_url=self.db_url,
        )
        self.assertEqual(backup_report["status"], "success")
        backup_file = Path(backup_report["backup_file"])
        checksum_file = Path(backup_report["checksum_file"])

        self.assertTrue(backup_file.exists())
        self.assertTrue(checksum_file.exists())
        self.assertGreater(backup_report["size_bytes"], 0)

        # 2. Simulate catastrophic loss by corrupting / removing database file
        self.engine.dispose()
        self.db_path.unlink()
        self.assertFalse(self.db_path.exists())

        # 3. Perform automated restoration
        restore_report = perform_restore(
            backup_path=backup_file,
            target_db=self.db_url,
            skip_migrations=True,
        )
        self.assertEqual(restore_report["status"], "success")
        self.assertTrue(self.db_path.exists())

        # 4. Connect to restored database and assert 100% data fidelity
        restored_engine = create_engine(self.db_url)
        with Session(restored_engine) as session:
            texts = list(session.exec(select(TextRecord)).all())
            self.assertEqual(len(texts), 1)
            self.assertEqual(texts[0].title, "Disaster Recovery Seed Story")
            self.assertEqual(texts[0].language, "German")

            sentences = list(session.exec(select(SentenceRecord)).all())
            self.assertEqual(len(sentences), 1)
            self.assertEqual(sentences[0].original_text, "Der Wiederherstellungstest ist erfolgreich.")

            sessions = list(session.exec(select(PracticeSessionRecord)).all())
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].net_wpm, 72.5)

            weak_words = list(session.exec(select(WeakWordRecord)).all())
            self.assertEqual(len(weak_words), 1)
            self.assertEqual(weak_words[0].word, "Wiederherstellungstest")

            usages = list(session.exec(select(TokenUsageRecord)).all())
            self.assertEqual(len(usages), 1)
            self.assertEqual(usages[0].total_tokens, 107)

        restored_engine.dispose()

    def test_restore_rejects_corrupted_or_tampered_backup(self):
        """Restore aborts with ValueError when checksum verification fails."""
        # 1. Create backup
        report = create_backup(
            output_dir=self.backup_dir,
            database_url=self.db_url,
        )
        backup_file = Path(report["backup_file"])

        # 2. Tamper with backup file by appending corrupt byte
        with open(backup_file, "ab") as f:
            f.write(b"CORRUPTED_EXTRA_DATA")

        # 3. Attempt restore and verify checksum rejection
        with self.assertRaises(ValueError) as ctx:
            perform_restore(
                backup_path=backup_file,
                target_db=self.db_url,
                skip_checksum=False,
                skip_migrations=True,
            )
        self.assertIn("Checksum verification failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
