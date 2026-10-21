"""Exercise fresh migrations, existing schema adoption, and rollback safety."""

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from core import database
from core.settings import Settings
from models.providers import ProviderCallRecord
from models.texts import TextRecord
from services.provider_governor import ProviderGovernor


class ProviderMigrationTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = create_engine(f"sqlite:///{folder}/migrations.sqlite")
        self.addCleanup(self.engine.dispose)
        self.enterContext(mock.patch.object(database, "engine", self.engine))
        self.config = Config("alembic.ini")
        self.config.set_main_option("script_location", "apps/backend/alembic")

    def test_upgrade_and_rollback_preserve_existing_library(self):
        previous = "0004_practice_sessions_and_weak_words"
        command.upgrade(self.config, previous)
        with Session(self.engine) as session:
            session.execute(text("INSERT INTO texts (title, language, owner_id, status, difficulty_level, word_count, completed_sentences, total_sentences, estimated_time_minutes) VALUES ('Keep me', 'French', 'reader', 'processed', 'Unrated', 1, 0, 1, 1)"))
            session.commit()
        command.upgrade(self.config, "head")
        governor = ProviderGovernor(self.engine, Settings())
        governor.reserve("groq", "test", "reader", "translation", 10, 10, 10)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(ProviderCallRecord)).all()), 1)
        command.downgrade(self.config, previous)
        self.assertNotIn("provider_calls", inspect(self.engine).get_table_names())
        command.upgrade(self.config, "head")
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(TextRecord)).one().title, "Keep me")

    def test_migration_adopts_existing_test_schema_without_losing_reservations(self):
        SQLModel.metadata.create_all(self.engine)
        governor = ProviderGovernor(self.engine, Settings())
        call_id = governor.reserve("deepseek", "test", "reader", "translation", 10, 10, 10)
        command.upgrade(self.config, "head")
        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(ProviderCallRecord, call_id))

    def test_intake_rollback_preserves_sources_and_refuses_unprepared_uploads(self):
        command.upgrade(self.config, "head")
        with Session(self.engine) as session:
            record = TextRecord(title="Queued source", owner_id="reader", source_text="A saved source.",
                                intake_options={"prepared": False}, status="processing")
            session.add(record)
            session.commit()
            text_id = record.id
        with self.assertRaisesRegex(RuntimeError, "Prepare or explicitly delete"):
            command.downgrade(self.config, "0005_provider_governance")
        with Session(self.engine) as session:
            record = session.get(TextRecord, text_id)
            assert record is not None
            self.assertEqual(record.source_text, "A saved source.")
            record.total_sentences = 1
            record.intake_options = {"prepared": True}
            session.add(record)
            session.commit()
        command.downgrade(self.config, "0005_provider_governance")
        self.assertIn("source_text", {column["name"] for column in inspect(self.engine).get_columns("texts")})
        command.upgrade(self.config, "head")
        with Session(self.engine) as session:
            record = session.get(TextRecord, text_id)
            assert record is not None
            self.assertEqual(record.source_text, "A saved source.")
