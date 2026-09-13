"""Tests for application factory, health endpoints, and offline mode."""

import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient
import sqlmodel
from sqlalchemy.exc import OperationalError

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from app import create_app
from core import database


class AppFactoryTests(unittest.TestCase):
    """Verify application factory behaviors under offline and degraded states."""

    def setUp(self) -> None:
        self.temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = sqlmodel.create_engine(
            f"sqlite:///{self.temp_dir}/test_factory.sqlite",
            connect_args={"check_same_thread": False},
        )
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

        self.enterContext(mock.patch.object(database, "engine", self.engine))
        self.enterContext(mock.patch.object(database, "init_db", lambda: None))

    def test_offline_boot_healthz_and_readyz(self) -> None:
        """App boots cleanly without API keys, serving /healthz and /readyz."""
        with mock.patch.dict(os.environ, {}, clear=True):
            app = create_app()
            client = TestClient(app)

            # Liveness probe
            health_res = client.get("/healthz")
            self.assertEqual(health_res.status_code, 200)
            self.assertEqual(health_res.json(), {"status": "ok"})

            # Readiness probe
            ready_res = client.get("/readyz")
            self.assertEqual(ready_res.status_code, 200)
            data = ready_res.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["database"], "connected")
            self.assertIn("llm_configured", data)

    def test_readyz_degraded_when_database_fails(self) -> None:
        """Readiness probe returns 503 degraded when the database connection fails."""
        app = create_app()
        client = TestClient(app)

        with mock.patch("app.Session") as mock_session:
            mock_session.side_effect = OperationalError("connection refused", {}, Exception("DB down"))
            res = client.get("/readyz")
            self.assertEqual(res.status_code, 503)
            data = res.json()
            self.assertEqual(data["status"], "degraded")
            self.assertIn("unhealthy", data["database"])
