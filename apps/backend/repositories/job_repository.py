"""Repository for durable background jobs with transactional leasing and retries."""

from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine, text
from sqlmodel import Session, select

from models.jobs import BackgroundJobRecord, utc_now


class JobRepository:
    """Manage transactional background jobs supporting concurrent workers."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enqueue(
        self,
        session: Session,
        owner_id: str,
        task_type: str,
        payload: Dict[str, Any],
        text_id: Optional[int] = None,
        max_retries: int = 3,
    ) -> BackgroundJobRecord:
        """Enqueue a background job within an existing database transaction."""
        job = BackgroundJobRecord(
            owner_id=owner_id,
            text_id=text_id,
            task_type=task_type,
            payload=payload,
            status="pending",
            attempt_count=0,
            max_retries=max_retries,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(job)
        session.flush()
        return job

    def claim_next_job(
        self,
        worker_id: str,
        lease_duration_seconds: int = 60,
    ) -> Optional[BackgroundJobRecord]:
        """Claim the next available pending or expired job.

        Uses SELECT ... FOR UPDATE SKIP LOCKED on PostgreSQL to prevent contention.
        Uses transactional select-and-update on SQLite for local testing.
        """
        now = utc_now()
        lease_until = now + timedelta(seconds=lease_duration_seconds)

        with Session(self._engine) as session:
            is_postgres = self._engine.dialect.name == "postgresql"

            if is_postgres:
                stmt = text(
                    """
                    SELECT id FROM background_jobs
                    WHERE (status = 'pending' AND (leased_until IS NULL OR leased_until <= :now))
                       OR (status = 'leased' AND leased_until < :now)
                    ORDER BY id ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
                result = session.execute(stmt, {"now": now}).first()
                if not result:
                    return None
                job_id = result[0]
                job = session.get(BackgroundJobRecord, job_id)
            else:
                statement = (
                    select(BackgroundJobRecord)
                    .where(
                        (
                            (BackgroundJobRecord.status == "pending")
                            & (
                                BackgroundJobRecord.leased_until.is_(None)  # pyright: ignore
                                | (BackgroundJobRecord.leased_until <= now)  # pyright: ignore
                            )
                        )
                        | (
                            (BackgroundJobRecord.status == "leased")
                            & (BackgroundJobRecord.leased_until < now)  # pyright: ignore
                        )
                    )
                    .order_by(BackgroundJobRecord.id.asc())  # pyright: ignore
                    .limit(1)
                )
                job = session.exec(statement).first()

            if not job or job.id is None:
                return None

            job.status = "leased"
            job.worker_id = worker_id
            job.leased_until = lease_until
            job.attempt_count += 1
            job.updated_at = now
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def heartbeat(
        self,
        job_id: int,
        worker_id: str,
        extend_seconds: int = 60,
    ) -> bool:
        """Extend the lease of a job currently held by worker_id."""
        now = utc_now()
        new_lease = now + timedelta(seconds=extend_seconds)

        with Session(self._engine) as session:
            job = session.get(BackgroundJobRecord, job_id)
            if not job or job.worker_id != worker_id or job.status != "leased":
                return False
            job.leased_until = new_lease
            job.updated_at = now
            session.add(job)
            session.commit()
            return True

    def complete(self, job_id: int, worker_id: str) -> bool:
        """Mark a job as successfully completed."""
        with Session(self._engine) as session:
            job = session.get(BackgroundJobRecord, job_id)
            if not job:
                return False
            if job.worker_id and job.worker_id != worker_id:
                return False
            job.status = "completed"
            job.leased_until = None
            job.updated_at = utc_now()
            session.add(job)
            session.commit()
            return True

    def fail(
        self,
        job_id: int,
        worker_id: str,
        error_message: str,
        backoff_base_seconds: int = 2,
    ) -> bool:
        """Record job failure. Transitions to dead_letter if max_retries exceeded, or pending with backoff."""
        with Session(self._engine) as session:
            job = session.get(BackgroundJobRecord, job_id)
            if not job or job.worker_id != worker_id:
                return False

            now = utc_now()
            job.error_message = error_message
            job.updated_at = now
            job.worker_id = None

            if job.attempt_count >= job.max_retries:
                job.status = "dead_letter"
                job.leased_until = None
            else:
                job.status = "pending"
                delay = (2 ** job.attempt_count) * backoff_base_seconds
                job.leased_until = now + timedelta(seconds=delay)

            session.add(job)
            session.commit()
            return True

    def reclaim_expired_leases(self) -> int:
        """Reset expired leased jobs back to pending."""
        now = utc_now()
        with Session(self._engine) as session:
            statement = select(BackgroundJobRecord).where(
                BackgroundJobRecord.status == "leased",
                BackgroundJobRecord.leased_until < now,  # pyright: ignore
            )
            expired = list(session.exec(statement).all())
            for job in expired:
                job.status = "pending"
                job.worker_id = None
                job.leased_until = None
                job.updated_at = now
                session.add(job)
            session.commit()
            return len(expired)

    def load_job(self, job_id: int) -> Optional[BackgroundJobRecord]:
        """Fetch a job by ID."""
        with Session(self._engine) as session:
            return session.get(BackgroundJobRecord, job_id)

    def load_jobs_by_text(
        self, text_id: int, owner_id: str
    ) -> List[BackgroundJobRecord]:
        """Fetch all jobs for a specific text and owner."""
        with Session(self._engine) as session:
            statement = (
                select(BackgroundJobRecord)
                .where(
                    BackgroundJobRecord.text_id == text_id,
                    BackgroundJobRecord.owner_id == owner_id,
                )
                .order_by(BackgroundJobRecord.id.asc())  # pyright: ignore
            )
            return list(session.exec(statement).all())
