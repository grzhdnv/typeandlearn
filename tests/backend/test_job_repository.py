"""Tests for transactional background job queue repository."""

from datetime import timedelta
import pathlib
import sys
import tempfile
import unittest

import sqlmodel
from sqlmodel import Session

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from models.jobs import BackgroundJobRecord, utc_now
from repositories.job_repository import JobRepository


class JobRepositoryTests(unittest.TestCase):
    """Verify transactional job queue operations, leasing, heartbeats, and backoff."""

    def setUp(self) -> None:
        self.temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = sqlmodel.create_engine(
            f"sqlite:///{self.temp_dir}/test_jobs.sqlite",
            connect_args={"check_same_thread": False},
        )
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.repo = JobRepository(self.engine)

    def test_enqueue_and_claim_job(self) -> None:
        """Jobs can be enqueued transactionally and claimed by a worker."""
        with Session(self.engine) as session:
            job = self.repo.enqueue(
                session=session,
                owner_id="owner_1",
                task_type="process_text",
                payload={"test": "data"},
                text_id=42,
            )
            session.commit()
            self.assertIsNotNone(job.id)
            self.assertEqual(job.status, "pending")

        claimed = self.repo.claim_next_job(worker_id="worker_a", lease_duration_seconds=30)
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed.worker_id, "worker_a")
        self.assertEqual(claimed.status, "leased")
        self.assertEqual(claimed.attempt_count, 1)
        self.assertIsNotNone(claimed.leased_until)

        # No other worker should claim it while leased
        second_claim = self.repo.claim_next_job(worker_id="worker_b", lease_duration_seconds=30)
        self.assertIsNone(second_claim)

    def test_heartbeat_extends_lease(self) -> None:
        """Worker heartbeats extend the active lease duration."""
        with Session(self.engine) as session:
            job = self.repo.enqueue(
                session=session,
                owner_id="owner_1",
                task_type="process_text",
                payload={},
            )
            session.commit()
            job_id = job.id
            assert job_id is not None

        claimed = self.repo.claim_next_job(worker_id="worker_a", lease_duration_seconds=10)
        assert claimed is not None
        initial_lease = claimed.leased_until

        # Wrong worker heartbeat fails
        self.assertFalse(self.repo.heartbeat(job_id, worker_id="wrong_worker", extend_seconds=60))

        # Right worker heartbeat succeeds and extends lease
        self.assertTrue(self.repo.heartbeat(job_id, worker_id="worker_a", extend_seconds=60))
        refreshed = self.repo.load_job(job_id)
        assert refreshed is not None
        assert refreshed.leased_until is not None
        assert initial_lease is not None
        self.assertGreater(refreshed.leased_until, initial_lease)

    def test_complete_job(self) -> None:
        """Completing a job marks it completed and clears lease."""
        with Session(self.engine) as session:
            job = self.repo.enqueue(session=session, owner_id="owner_1", task_type="task", payload={})
            session.commit()
            job_id = job.id
            assert job_id is not None

        self.repo.claim_next_job(worker_id="worker_a")
        self.assertTrue(self.repo.complete(job_id, worker_id="worker_a"))

        completed = self.repo.load_job(job_id)
        assert completed is not None
        self.assertEqual(completed.status, "completed")
        self.assertIsNone(completed.leased_until)

    def test_fail_with_exponential_backoff_and_dead_letter(self) -> None:
        """Failing jobs retry with exponential backoff and transition to dead_letter after max retries."""
        with Session(self.engine) as session:
            job = self.repo.enqueue(
                session=session,
                owner_id="owner_1",
                task_type="flaky_task",
                payload={},
                max_retries=3,
            )
            session.commit()
            job_id = job.id
            assert job_id is not None

        # Attempt 1
        claimed1 = self.repo.claim_next_job(worker_id="w1")
        assert claimed1 is not None
        self.assertEqual(claimed1.attempt_count, 1)
        self.repo.fail(job_id, worker_id="w1", error_message="Network error 1", backoff_base_seconds=1)

        job_state = self.repo.load_job(job_id)
        assert job_state is not None
        self.assertEqual(job_state.status, "pending")
        self.assertEqual(job_state.error_message, "Network error 1")
        # Leased until should be in future due to backoff (2^1 * 1s = 2s)
        leased_until = job_state.leased_until
        assert leased_until is not None
        if leased_until.tzinfo is None:
            from datetime import timezone
            leased_until = leased_until.replace(tzinfo=timezone.utc)
        self.assertGreater(leased_until, utc_now() - timedelta(seconds=1))

        # Simulate backoff elapsed
        with Session(self.engine) as session:
            db_job = session.get(BackgroundJobRecord, job_id)
            assert db_job is not None
            db_job.leased_until = utc_now() - timedelta(seconds=10)
            session.add(db_job)
            session.commit()

        # Attempt 2
        claimed2 = self.repo.claim_next_job(worker_id="w2")
        assert claimed2 is not None
        self.assertEqual(claimed2.attempt_count, 2)
        self.repo.fail(job_id, worker_id="w2", error_message="Network error 2", backoff_base_seconds=1)

        # Simulate backoff elapsed
        with Session(self.engine) as session:
            db_job = session.get(BackgroundJobRecord, job_id)
            assert db_job is not None
            db_job.leased_until = utc_now() - timedelta(seconds=10)
            session.add(db_job)
            session.commit()

        # Attempt 3 (Final attempt reaching max_retries=3)
        claimed3 = self.repo.claim_next_job(worker_id="w3")
        assert claimed3 is not None
        self.assertEqual(claimed3.attempt_count, 3)
        self.repo.fail(job_id, worker_id="w3", error_message="Fatal crash", backoff_base_seconds=1)

        dead_job = self.repo.load_job(job_id)
        assert dead_job is not None
        self.assertEqual(dead_job.status, "dead_letter")
        self.assertEqual(dead_job.error_message, "Fatal crash")
        self.assertIsNone(dead_job.leased_until)

    def test_reclaim_expired_leases(self) -> None:
        """Expired leases are reclaimed and made available for claiming again."""
        with Session(self.engine) as session:
            job = self.repo.enqueue(session=session, owner_id="owner_1", task_type="task", payload={})
            session.commit()
            job_id = job.id
            assert job_id is not None

        # Claim with an already-expired lease
        claimed = self.repo.claim_next_job(worker_id="crashed_worker", lease_duration_seconds=-10)
        assert claimed is not None

        reclaimed_count = self.repo.reclaim_expired_leases()
        self.assertEqual(reclaimed_count, 1)

        reclaimed_job = self.repo.load_job(job_id)
        assert reclaimed_job is not None
        self.assertEqual(reclaimed_job.status, "pending")
        self.assertIsNone(reclaimed_job.worker_id)

    def test_load_jobs_by_text(self) -> None:
        """Loading jobs by text and owner retrieves only matching records."""
        with Session(self.engine) as session:
            self.repo.enqueue(session, owner_id="owner_1", task_type="t1", payload={}, text_id=10)
            self.repo.enqueue(session, owner_id="owner_1", task_type="t2", payload={}, text_id=10)
            self.repo.enqueue(session, owner_id="owner_2", task_type="t3", payload={}, text_id=10)
            self.repo.enqueue(session, owner_id="owner_1", task_type="t4", payload={}, text_id=20)
            session.commit()

        jobs = self.repo.load_jobs_by_text(text_id=10, owner_id="owner_1")
        self.assertEqual(len(jobs), 2)
        self.assertEqual({j.task_type for j in jobs}, {"t1", "t2"})
