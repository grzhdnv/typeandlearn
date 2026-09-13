"""Background worker daemon for processing durable background jobs."""

import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

sys.path.append(str(Path(__file__).resolve().parent))

from repositories.job_repository import JobRepository
from services.text_service import TextService

logger = logging.getLogger("typeandlearn.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class HeartbeatThread(threading.Thread):
    """Periodically heartbeats a leased job in the background to prevent expiration."""

    def __init__(
        self,
        job_repo: JobRepository,
        job_id: int,
        worker_id: str,
        interval: int = 25,
    ) -> None:
        super().__init__(daemon=True)
        self.job_repo = job_repo
        self.job_id = job_id
        self.worker_id = worker_id
        self.interval = interval
        self.stop_event = threading.Event()

    def run(self) -> None:
        """Run periodic heartbeat until explicitly stopped."""
        while not self.stop_event.wait(self.interval):
            success = self.job_repo.heartbeat(
                self.job_id,
                self.worker_id,
                extend_seconds=self.interval * 2,
            )
            if not success:
                logger.warning("Heartbeat failed for job %s held by worker %s", self.job_id, self.worker_id)
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
        self.worker_id = worker_id or os.getenv("WORKER_ID", f"worker-{uuid4().hex[:8]}")
        self.lease_duration = lease_duration
        self.poll_interval = poll_interval
        self._shutdown = False

    def request_shutdown(self) -> None:
        """Signal the worker loop to stop after the current iteration."""
        logger.info("Shutdown requested for worker %s", self.worker_id)
        self._shutdown = True

    def process_one_job(self) -> bool:
        """Claim and process one job from the queue. Returns True if a job was processed."""
        # Clean up any expired leases from crashed workers
        self.job_repo.reclaim_expired_leases()

        job = self.job_repo.claim_next_job(
            worker_id=self.worker_id,
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
            worker_id=self.worker_id,
            interval=max(5, self.lease_duration // 2),
        )
        heartbeat.start()

        try:
            if job.task_type == "process_text":
                if job.text_id is not None:
                    self.text_service.process_pending_text(job.text_id, job.owner_id)
                self.job_repo.complete(job.id, self.worker_id)
                logger.info("Worker %s successfully completed job %s", self.worker_id, job.id)
            else:
                error_msg = f"Unknown task type: {job.task_type}"
                logger.error(error_msg)
                self.job_repo.fail(job.id, self.worker_id, error_msg)
        except Exception as err:
            logger.exception("Error processing job %s: %s", job.id, err)
            self.job_repo.fail(job.id, self.worker_id, str(err))
        finally:
            heartbeat.stop()

        return True

    def run(self, single_run: bool = False) -> None:
        """Run the main worker processing loop."""
        logger.info("Starting background worker %s", self.worker_id)

        while not self._shutdown:
            try:
                processed = self.process_one_job()
                if single_run:
                    break
                if not processed:
                    time.sleep(self.poll_interval)
            except Exception as loop_err:
                logger.exception("Unexpected error in worker loop: %s", loop_err)
                if single_run:
                    break
                time.sleep(self.poll_interval)

        logger.info("Worker %s stopped cleanly.", self.worker_id)


def main() -> None:
    """CLI entrypoint for standalone worker container/process."""
    from app_state import job_repository, text_service

    worker = Worker(job_repo=job_repository, text_service=text_service)

    def handle_signal(sig, frame):
        worker.request_shutdown()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    worker.run()


if __name__ == "__main__":
    main()
