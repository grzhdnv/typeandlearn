"""Opt-in live PostgreSQL acceptance; never uses the development database.

Run with TYPEANDLEARN_TEST_POSTGRES_URL pointing to a disposable database named
`typeandlearn_acceptance`. Each case owns a fresh schema and removes only that schema.
"""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine

sys.path.append(str(Path(__file__).resolve().parents[2] / "apps/backend"))

from core.settings import Settings
from models.texts import TextRecord
from repositories.job_repository import JobRepository
from repositories.text_repository import TextRepository
from services.provider_governor import ProviderGovernor, QuotaUnavailable
from services.text_service import TextService
from worker import Worker

ROOT = Path(__file__).resolve().parents[2]
URL = os.getenv("TYPEANDLEARN_TEST_POSTGRES_URL")


@unittest.skipUnless(URL, "Set TYPEANDLEARN_TEST_POSTGRES_URL for live PostgreSQL acceptance")
class PostgreSQLAcceptanceTests(unittest.TestCase):
    def setUp(self):
        assert URL is not None
        url = make_url(URL)
        if url.get_backend_name() != "postgresql" or url.database != "typeandlearn_acceptance":
            self.fail("Acceptance requires a disposable PostgreSQL database named typeandlearn_acceptance")
        self.schema = "tal_acceptance_" + uuid4().hex
        self.admin = create_engine(url)
        self.addCleanup(self.admin.dispose)
        with self.admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addCleanup(self.drop_schema)
        self.url = url.update_query_dict({"options": f"-csearch_path={self.schema}"}).render_as_string(hide_password=False)
        self.engine = create_engine(self.url, pool_size=16, max_overflow=0)
        self.addCleanup(self.engine.dispose)
        self.repo = JobRepository(self.engine)
        self.env = {
            **os.environ, "DATABASE_URL": self.url, "GROQ_API_KEY": "",
            "OPENROUTER_API_KEY": "", "DEEPSEEK_API_KEY": "",
            "EMBEDDED_WORKER_ENABLED": "false", "AUTH_MODE": "local",
            "PYTHONPATH": str(ROOT / "apps/backend"),
        }

    def drop_schema(self):
        with self.admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    def process(self, code, *, timeout=45):
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=self.env,
                                capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def migrate(self, target="head", direction="upgrade"):
        return subprocess.run([sys.executable, "-m", "alembic", direction, target],
                              cwd=ROOT, env=self.env, capture_output=True, text=True, timeout=30)

    def head(self):
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def enqueue(self, owner="owner_1", text_id: int | None = None, max_retries=3) -> tuple[int, int]:
        with Session(self.engine) as session:
            if text_id is None:
                record = TextRecord(owner_id=owner, title="Synthetic", status="processing")
                session.add(record)
                session.flush()
                text_id = record.id
            assert text_id is not None
            job = self.repo.enqueue(session, owner, "process_text", {}, text_id=text_id,
                                    max_retries=max_retries)
            session.commit()
            assert job.id is not None
            return job.id, text_id

    def test_populated_upgrade_and_source_preserving_rollback(self):
        result = self.migrate("0005_provider_governance")
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO texts (owner_id, title, total_sentences) VALUES ('reader', 'Existing library', 1)"))
        self.head()
        with Session(self.engine) as session:
            raw = TextRecord(owner_id="reader", title="Synthetic", source_text="Hallo Welt.",
                             intake_options={"prepared": False}, status="processing")
            session.add(raw)
            session.commit()
            raw_id = raw.id
        refused = self.migrate("0005_provider_governance", "downgrade")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("Prepare or explicitly delete", refused.stderr)
        with Session(self.engine) as session:
            raw = session.get(TextRecord, raw_id)
            assert raw is not None
            self.assertEqual(raw.source_text, "Hallo Welt.")
            raw.total_sentences = 1
            raw.intake_options = {"prepared": True}
            session.add(raw)
            session.commit()
        result = self.migrate("0005_provider_governance", "downgrade")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.head()
        self.head()
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM texts")).scalar(), 2)
            self.assertEqual(connection.execute(text("SELECT source_text FROM texts WHERE id=:id"), {"id": raw_id}).scalar(), "Hallo Welt.")

    def test_existing_schema_and_narrow_version_table_are_adopted(self):
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
            connection.execute(text("INSERT INTO texts (owner_id, title, status, language, difficulty_level, word_count, completed_sentences, total_sentences, estimated_time_minutes) VALUES ('reader', 'Adopted', 'processed', 'German', 'A1', 1, 0, 1, 1)"))
        self.head()
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT title FROM texts")).scalar(), "Adopted")
            self.assertEqual(connection.execute(text("SELECT character_maximum_length FROM information_schema.columns WHERE table_schema=:schema AND table_name='alembic_version' AND column_name='version_num'"), {"schema": self.schema}).scalar(), 128)

    def test_concurrent_api_and_worker_migration_startup(self):
        # Both entrypoints call init_db. Independent interpreters exercise Alembic's
        # real DDL/version-table race rather than mocking migration operations.
        self.process('''
from concurrent.futures import ThreadPoolExecutor
import os, subprocess, sys
code = "from core.database import init_db; init_db()"
with ThreadPoolExecutor(max_workers=6) as pool:
    runs = list(pool.map(lambda _: subprocess.run([sys.executable, "-c", code], env=os.environ,
                    capture_output=True, text=True, timeout=30), range(6)))
failures = [p.stderr for p in runs if p.returncode]
assert not failures, "\\n".join(failures)
''')
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT version_num FROM alembic_version")).scalar(), "0006_durable_intake")

    def test_parallel_claimers_and_legacy_duplicate_text_jobs(self):
        self.head()
        jobs = [self.enqueue() for _ in range(8)]
        barrier = threading.Barrier(16)
        def claim(index):
            barrier.wait(timeout=10)
            return self.repo.claim_next_job(f"claimer-{index}")
        with ThreadPoolExecutor(max_workers=16) as pool:
            claimed = list(pool.map(claim, range(16)))
        self.assertCountEqual([j.id for j in claimed if j], [j[0] for j in jobs])
        for job in claimed:
            if job:
                assert job.id is not None and job.worker_id is not None
                self.assertTrue(self.repo.complete(job.id, job.worker_id))
        first_id, text_id = self.enqueue()
        second_id, _ = self.enqueue(text_id=text_id)
        with ThreadPoolExecutor(max_workers=16) as pool:
            duplicates = list(pool.map(claim, range(16)))
        leases = [j for j in duplicates if j]
        self.assertEqual(len(leases), 1)
        self.assertEqual(leases[0].id, first_id)
        lease_owner = leases[0].worker_id
        assert lease_owner is not None
        self.assertTrue(self.repo.complete(first_id, lease_owner))
        next_job = self.repo.claim_next_job("next")
        assert next_job is not None
        self.assertEqual(next_job.id, second_id)

    def test_expiry_fencing_final_crash_and_retry_budget(self):
        self.head()
        job_id, _ = self.enqueue(max_retries=2)
        self.repo.claim_next_job("stale", lease_duration_seconds=-1)
        self.assertFalse(self.repo.heartbeat(job_id, "stale"))
        replacement = self.repo.claim_next_job("replacement")
        assert replacement is not None
        self.assertEqual(replacement.attempt_count, 2)
        self.assertFalse(self.repo.complete(job_id, "stale"))
        self.assertFalse(self.repo.fail(job_id, "stale", "late error"))
        self.assertTrue(self.repo.fail(job_id, "replacement", "synthetic failure"))
        dead_job = self.repo.load_job(job_id)
        assert dead_job is not None
        self.assertEqual(dead_job.status, "dead_letter")
        final_id, text_id = self.enqueue(max_retries=1)
        self.repo.claim_next_job("crashed", lease_duration_seconds=-1)
        self.assertEqual(self.repo.reclaim_expired_leases(), 1)
        final_job = self.repo.load_job(final_id)
        assert final_job is not None
        self.assertEqual(final_job.status, "dead_letter")
        self.assertIsNone(self.repo.claim_next_job("replacement"))
        failed_text = TextRepository(self.engine).load_one_text(text_id, "owner_1")
        assert failed_text is not None
        self.assertEqual(failed_text.status, "failed")

    def test_heartbeat_and_concurrent_retry(self):
        self.head()
        job_id, text_id = self.enqueue()
        service = mock.Mock(spec=TextService)
        entered, release = threading.Event(), threading.Event()
        def slow(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(10))
            kwargs["ensure_lease"]()
        service.process_pending_text.side_effect = slow
        worker = Worker(self.repo, service, lease_duration=1)
        with ThreadPoolExecutor(max_workers=1) as pool:
            run = pool.submit(worker.process_one_job)
            try:
                self.assertTrue(entered.wait(10))
                time.sleep(1.3)
                self.assertIsNone(self.repo.claim_next_job("competitor"))
                with self.assertRaisesRegex(ValueError, "already running"):
                    TextRepository(self.engine).queue_enrichment(text_id, "owner_1")
            finally:
                release.set()
            self.assertTrue(run.result(timeout=10))
        completed_job = self.repo.load_job(job_id)
        assert completed_job is not None
        self.assertEqual(completed_job.status, "completed")
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: TextRepository(self.engine).queue_enrichment(text_id, "owner_1"), range(8)))
        jobs = self.repo.load_jobs_by_text(text_id, "owner_1")
        self.assertEqual(sum(j.status == "pending" for j in jobs), 1)

    def test_shared_provider_reservations_are_atomic(self):
        self.head()
        cfg = Settings(groq_rpm=2, groq_tpm=6400)
        barrier = threading.Barrier(8)
        def reserve(index):
            barrier.wait(timeout=10)
            try:
                ProviderGovernor(self.engine, cfg).reserve("groq", "synthetic", f"reader-{index}", "translation", 10, 10, 10)
                return True
            except QuotaUnavailable:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(reserve, range(8))), 2)

    def test_api_lifespan_resumes_another_owners_raw_source_offline(self):
        self.head()
        self.process('''
import time
from fastapi.testclient import TestClient
from app import create_app
from app_state import text_service, job_repository
from core.settings import Settings
record = text_service.upload("Hallo Welt. Das ist ein Test.", owner_id="another-reader", language="German")
with TestClient(create_app(Settings(embedded_worker_enabled=True))) as client:
    assert client.get(f"/texts/{record.id}").status_code == 404
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        data = text_service.get_one(str(record.id), "another-reader")
        if data.status == "failed" and data.total_sentences == 2:
            break
        time.sleep(.05)
    else:
        raise AssertionError("API did not resume another owner's queued source")
    assert data.source_text == "Hallo Welt. Das ist ein Test."
    assert data.enrichment_stage == "failed"
    assert len(job_repository.load_jobs_by_text(record.id, "another-reader")) == 1
''')

    def test_real_http_api_and_two_cli_workers(self):
        self.process('''
import json, os, signal, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from sqlalchemy import create_engine, text
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
engine = create_engine(os.environ["DATABASE_URL"])
base = f"http://127.0.0.1:{port}"
api_code = """
from contextlib import asynccontextmanager
from pathlib import Path
import os, uvicorn
from apps.backend.main import app
original_lifespan = app.router.lifespan_context
@asynccontextmanager
async def measured_lifespan(application):
    async with original_lifespan(application):
        yield
    Path(os.environ["TYPEANDLEARN_SHUTDOWN_MARKER"]).write_text("complete")
app.router.lifespan_context = measured_lifespan
uvicorn.run(app, host="127.0.0.1", port=int(os.environ["TYPEANDLEARN_API_PORT"]))
"""
commands = [
    [sys.executable, "-c", api_code],
    [sys.executable, "apps/backend/worker.py"],
    [sys.executable, "apps/backend/worker.py"],
]
processes = []
with tempfile.TemporaryDirectory() as scratch, tempfile.TemporaryFile(mode="w+") as logs:
    marker = Path(scratch) / "api-shutdown-complete"
    env = {**os.environ, "TYPEANDLEARN_SHUTDOWN_MARKER": str(marker), "TYPEANDLEARN_API_PORT": str(port)}
    try:
        for command in commands:
            processes.append(subprocess.Popen(command, env=env, stdout=logs, stderr=logs))
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert all(p.poll() is None for p in processes), "API/worker exited during startup"
            try:
                with urllib.request.urlopen(base + "/readyz", timeout=1) as response:
                    assert json.load(response)["database"] == "connected"
                break
            except OSError:
                time.sleep(.1)
        else:
            raise AssertionError("API readiness timeout")
        payload = json.dumps({"text": "Hallo Welt. Das ist ein Test.", "language": "German"}).encode()
        request = urllib.request.Request(base + "/texts", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            text_id = json.load(response)["id"]
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with urllib.request.urlopen(base + f"/texts/{text_id}", timeout=2) as response:
                data = json.load(response)["data"]
            if data["status"] == "failed" and data["total_sentences"] == 2:
                break
            time.sleep(.05)
        else:
            raise AssertionError("CLI workers did not prepare saved source")
        assert data["source_text"] == "Hallo Welt. Das ist ein Test."
        with engine.connect() as connection:
            row = connection.execute(text("SELECT status, attempt_count FROM background_jobs WHERE text_id=:id AND owner_id='owner_local_default'"), {"id": text_id}).one()
            assert row.status == "pending" and row.attempt_count == 1
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        engine.dispose()
    # Uvicorn re-raises SIGTERM after graceful lifespan shutdown. The marker
    # proves shutdown completed instead of accepting any signal-killed process.
    assert marker.read_text() == "complete"
    assert processes[0].returncode in (0, -signal.SIGTERM)
    assert all(p.returncode == 0 for p in processes[1:]), "Unclean worker shutdown"
''', timeout=55)

    def test_real_process_crash_and_preparation_checkpoint_recovery(self):
        self.head()
        # Abrupt exit after the real preparation commit; no provider or dictionary
        # call is allowed. The replacement must retain sentence IDs and progress.
        self.process('''
import os, subprocess, sys
from sqlmodel import Session
from app_state import text_service, job_repository, text_repository
from core.database import engine
from models.jobs import utc_now, BackgroundJobRecord
from datetime import timedelta
record = text_service.upload("Hallo Welt. Das ist ein Test.", owner_id="crash-reader", language="German")
code = """
import os
from app_state import text_service
from worker import Worker
class CrashWorkerService:
    def process_pending_text(self, text_id, owner_id, *, ensure_lease):
        record = text_service._repository.load_one_text(text_id, owner_id)
        text_service._prepare_intake(record, ensure_lease)
        os._exit(23)
from app_state import job_repository
Worker(job_repository, CrashWorkerService(), lease_duration=1).process_one_job()
"""
result = subprocess.run([sys.executable, "-c", code], env=os.environ, timeout=25)
assert result.returncode == 23
sentences = text_repository.load_sentences(record.id, "crash-reader")
assert len(sentences) == 2
ids = [s.id for s in sentences]
text_repository.update_progress(record.id, "crash-reader", 0)
with Session(engine) as session:
    job = session.get(BackgroundJobRecord, job_repository.load_jobs_by_text(record.id, "crash-reader")[0].id)
    job.leased_until = utc_now() - timedelta(seconds=1)
    session.add(job)
    session.commit()
from worker import Worker
assert Worker(job_repository, text_service).process_one_job()
assert [s.id for s in text_repository.load_sentences(record.id, "crash-reader")] == ids
saved = text_service.get_one(str(record.id), "crash-reader")
assert saved.completed_sentence_indices == [0]
assert saved.source_text == "Hallo Welt. Das ist ein Test."
assert saved.status == "failed"
assert job_repository.load_jobs_by_text(record.id, "crash-reader")[0].attempt_count == 2
''')
