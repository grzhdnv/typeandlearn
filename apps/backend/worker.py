"""Background worker daemon for processing durable background jobs."""

import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Optional
from uuid import uuid4

sys.path.append(str(Path(__file__).resolve().parent))

from repositories.job_repository import JobRepository, LeaseLostError
from services.text_service import TextService

logger = logging.getLogger("typeandlearn.worker")


class HeartbeatThread(threading.Thread):
    """Periodically heartbeats a leased job in the background to prevent expiration."""

    def __init__(
        self,
        job_repo: JobRepository,
        job_id: int,
        worker_id: str,
        interval: float = 25,
        extend_seconds: int = 60,
    ) -> None:
        super().__init__(daemon=True)
        self.job_repo = job_repo
        self.job_id = job_id
        self.worker_id = worker_id
        self.interval = interval
        self.extend_seconds = extend_seconds
        self.stop_event = threading.Event()

    def run(self) -> None:
        """Run periodic heartbeat until explicitly stopped."""
        while not self.stop_event.wait(self.interval):
            try:
                success = self.job_repo.heartbeat(
                    self.job_id,
                    self.worker_id,
                    extend_seconds=self.extend_seconds,
                )
            except Exception:
                logger.warning("Heartbeat unavailable for job %s", self.job_id)
                continue
            if not success:
                logger.warning(
                    "Heartbeat failed for job %s held by worker %s",
                    self.job_id,
                    self.worker_id,
                )
                break

    def stop(self) -> None:
        """Signal heartbeat thread to terminate."""
        self.stop_event.set()


class Worker:
    """Consumes and executes background jobs from the durable PostgreSQL/SQLite queue."""

    def __init__(
        self,
        job_repo: JobRepository,
        text_service: TextService,
        worker_id: Optional[str] = None,
        lease_duration: int = 60,
        poll_interval: float = 1.0,
    ) -> None:
        self.job_repo = job_repo
        self.text_service = text_service
        self.worker_id = worker_id or os.getenv(
            "WORKER_ID", f"worker-{uuid4().hex[:8]}"
        )
        self.lease_duration = lease_duration
        self.poll_interval = poll_interval
        self._shutdown = threading.Event()
        if lease_duration <= 0:
            raise ValueError("Lease duration must be positive")

    def request_shutdown(self) -> None:
        """Signal the worker loop to stop after the current iteration."""
        logger.info("Shutdown requested for worker %s", self.worker_id)
        self._shutdown.set()

    def process_one_job(self) -> bool:
        """Claim and process one job from the queue. Returns True if a job was processed."""
        lease_owner = f"{self.worker_id}:{uuid4().hex}"
        job = self.job_repo.claim_next_job(
            worker_id=lease_owner,
            lease_duration_seconds=self.lease_duration,
        )
        if not job or job.id is None:
            return False

        logger.info(
            "Worker %s claimed job %s (type: %s, text_id: %s, attempt: %d)",
            self.worker_id,
            job.id,
            job.task_type,
            job.text_id,
            job.attempt_count,
        )

        heartbeat = HeartbeatThread(
            job_repo=self.job_repo,
            job_id=job.id,
            worker_id=lease_owner,
            interval=self.lease_duration / 3,
            extend_seconds=self.lease_duration,
        )
        heartbeat.start()

        job_id = job.id

        def ensure_lease() -> None:
            if not self.job_repo.owns_lease(job_id, lease_owner):
                raise LeaseLostError("Worker no longer owns this job")

        try:
            if job.task_type != "process_text" or job.text_id is None:
                raise ValueError("Unsupported job type or missing text ID")
            self.text_service.process_pending_text(
                job.text_id, job.owner_id, ensure_lease=ensure_lease
            )
            if self.job_repo.complete(job.id, lease_owner):
                logger.info("Worker %s completed job %s", self.worker_id, job.id)
        except LeaseLostError:
            logger.warning("Worker %s lost lease for job %s", self.worker_id, job.id)
        except Exception as err:
            # Upstream exceptions can contain prompts; keep only the error class.
            logger.warning("Job %s failed (%s)", job.id, type(err).__name__)
            self.job_repo.fail(
                job.id, lease_owner, f"Enrichment failed ({type(err).__name__})"
            )
        finally:
            heartbeat.stop()
            heartbeat.join()

        return True

    def run(self, single_run: bool = False) -> None:
        """Run the main worker processing loop."""
        logger.info("Starting background worker %s", self.worker_id)

        while not self._shutdown.is_set():
            try:
                processed = self.process_one_job()
                if single_run:
                    break
                if not processed:
                    self._shutdown.wait(self.poll_interval)
            except Exception as loop_err:
                logger.error("Worker iteration failed (%s)", type(loop_err).__name__)
                if single_run:
                    break
                self._shutdown.wait(self.poll_interval)

        logger.info("Worker %s stopped cleanly.", self.worker_id)


def main() -> None:
    """CLI entrypoint for standalone worker container/process."""
    from app_state import job_repository, text_service
    from core.database import init_db
    from core.logging import setup_logging

    setup_logging()
    init_db()

    worker = Worker(job_repo=job_repository, text_service=text_service)

    def handle_signal(sig, frame):
        worker.request_shutdown()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    worker.run()


if __name__ == "__main__":
    main()
