"""Tests for the standalone background worker daemon."""

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import sqlmodel
from sqlmodel import Session

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from repositories.job_repository import JobRepository
from services.text_service import TextService
from worker import Worker


class WorkerTests(unittest.TestCase):
    """Verify background worker claiming, execution, heartbeats, and error recovery."""

    def setUp(self) -> None:
        self.temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = sqlmodel.create_engine(
            f"sqlite:///{self.temp_dir}/test_worker.sqlite",
            connect_args={"check_same_thread": False},
        )
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

        self.job_repo = JobRepository(self.engine)
        self.text_service = mock.Mock(spec=TextService)
        self.worker = Worker(
            job_repo=self.job_repo,
            text_service=self.text_service,
            worker_id="test_worker_1",
            lease_duration=10,
        )

    def test_process_no_job(self) -> None:
        """When queue is empty, process_one_job returns False."""
        processed = self.worker.process_one_job()
        self.assertFalse(processed)

    def test_process_text_job_success(self) -> None:
        """Worker successfully claims and completes process_text job."""
        with Session(self.engine) as session:
            job = self.job_repo.enqueue(
                session=session,
                owner_id="owner_1",
                task_type="process_text",
                payload={"language": "German"},
                text_id=101,
            )
            session.commit()
            job_id = job.id
            assert job_id is not None

        processed = self.worker.process_one_job()
        self.assertTrue(processed)

        # Verify text_service was called
        self.text_service.process_pending_text.assert_called_once_with(101, "owner_1")

        # Verify job is completed
        completed_job = self.job_repo.load_job(job_id)
        assert completed_job is not None
        self.assertEqual(completed_job.status, "completed")

    def test_process_unknown_task_fails(self) -> None:
        """Worker marks unknown task types as failed."""
        with Session(self.engine) as session:
            job = self.job_repo.enqueue(
                session=session,
                owner_id="owner_1",
                task_type="mystery_task",
                payload={},
                text_id=202,
            )
            session.commit()
            job_id = job.id
            assert job_id is not None

        processed = self.worker.process_one_job()
        self.assertTrue(processed)

        failed_job = self.job_repo.load_job(job_id)
        assert failed_job is not None
        self.assertEqual(failed_job.status, "pending")  # in retry backoff
        self.assertIn("Unknown task type", failed_job.error_message or "")

    def test_process_job_exception_handling(self) -> None:
        """Worker catches service exceptions, logs them, and fails the job with backoff."""
        with Session(self.engine) as session:
            job = self.job_repo.enqueue(
                session=session,
                owner_id="owner_1",
                task_type="process_text",
                payload={},
                text_id=303,
            )
            session.commit()
            job_id = job.id
            assert job_id is not None

        self.text_service.process_pending_text.side_effect = RuntimeError("NLP pipeline crashed")

        processed = self.worker.process_one_job()
        self.assertTrue(processed)

        failed_job = self.job_repo.load_job(job_id)
        assert failed_job is not None
        self.assertEqual(failed_job.status, "pending")  # in retry backoff
        self.assertIn("NLP pipeline crashed", failed_job.error_message or "")

    def test_worker_run_single_run(self) -> None:
        """Worker run with single_run=True terminates immediately after loop pass."""
        self.worker.run(single_run=True)
        # Should finish cleanly without infinite loop
