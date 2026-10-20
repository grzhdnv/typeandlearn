"""Repository for durable background jobs with transactional leasing and retries."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine, text
from sqlmodel import Session, col, select
from sqlalchemy.orm import aliased

from models.jobs import BackgroundJobRecord, utc_now
from models.texts import TextRecord


class LeaseLostError(RuntimeError):
    """The worker must stop writing after losing its lease."""


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

    def _lock(self, session: Session) -> None:
        if self._engine.dialect.name == "sqlite":
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        elif self._engine.dialect.name != "postgresql":
            raise ValueError("Job leases require SQLite or PostgreSQL")

    def _leased_job(
        self, session: Session, job_id: int, worker_id: str
    ) -> Optional[BackgroundJobRecord]:
        self._lock(session)
        return session.exec(
            select(BackgroundJobRecord)
            .where(
                BackgroundJobRecord.id == job_id,
                BackgroundJobRecord.worker_id == worker_id,
                BackgroundJobRecord.status == "leased",
                col(BackgroundJobRecord.leased_until) > utc_now(),  # pyright: ignore
            )
            .with_for_update()
        ).first()

    def claim_next_job(
        self, worker_id: str, lease_duration_seconds: int = 60
    ) -> Optional[BackgroundJobRecord]:
        """Serialize SQLite claims; skip locked PostgreSQL rows across all tenants.

        Queue consumers are privileged: owner_id is taken from the claimed row,
        never from an API request. Every subsequent text operation is owner-scoped.
        """
        with Session(self._engine) as session:
            self._lock(session)
            now = utc_now()
            self._reclaim(session, now)
            active = aliased(BackgroundJobRecord)
            busy_text = (
                select(active.id)
                .where(
                    active.owner_id == BackgroundJobRecord.owner_id,
                    active.text_id == BackgroundJobRecord.text_id,
                    active.status == "leased",
                )
                .exists()
            )
            job = session.exec(
                select(BackgroundJobRecord)
                .where(
                    BackgroundJobRecord.status == "pending",
                    ~busy_text,
                    (
                        col(BackgroundJobRecord.leased_until).is_(None)  # pyright: ignore
                        | (col(BackgroundJobRecord.leased_until) <= now)
                    ),  # pyright: ignore
                    BackgroundJobRecord.attempt_count < BackgroundJobRecord.max_retries,
                )
                .order_by(col(BackgroundJobRecord.id))
                .limit(1)
                .with_for_update(skip_locked=True)
            ).first()  # pyright: ignore
            if job is None:
                session.commit()
                return None
            if self._engine.dialect.name == "postgresql" and job.text_id is not None:
                # Distinct legacy jobs for one text must also serialize across workers.
                locked = session.execute(
                    text("SELECT pg_try_advisory_xact_lock(:text_id)"),
                    {"text_id": job.text_id},
                ).scalar()
                if (
                    not locked
                    or session.exec(
                        select(BackgroundJobRecord.id).where(
                            BackgroundJobRecord.owner_id == job.owner_id,
                            BackgroundJobRecord.text_id == job.text_id,
                            BackgroundJobRecord.status == "leased",
                        )
                    ).first()
                    is not None
                ):
                    session.commit()
                    return None
            job.status = "leased"
            job.worker_id = worker_id
            job.leased_until = now + timedelta(seconds=lease_duration_seconds)
            job.attempt_count += 1
            job.updated_at = now
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def owns_lease(self, job_id: int, worker_id: str) -> bool:
        with Session(self._engine) as session:
            return (
                session.exec(
                    select(BackgroundJobRecord.id).where(
                        BackgroundJobRecord.id == job_id,
                        BackgroundJobRecord.worker_id == worker_id,
                        BackgroundJobRecord.status == "leased",
                        col(BackgroundJobRecord.leased_until) > utc_now(),  # pyright: ignore
                    )
                ).first()
                is not None
            )

    def heartbeat(self, job_id: int, worker_id: str, extend_seconds: int = 60) -> bool:
        """Only a currently valid lease can be renewed; expired leases stay lost."""
        with Session(self._engine) as session:
            job = self._leased_job(session, job_id, worker_id)
            if job is None:
                return False
            job.leased_until = utc_now() + timedelta(seconds=extend_seconds)
            job.updated_at = utc_now()
            session.add(job)
            session.commit()
            return True

    def complete(self, job_id: int, worker_id: str) -> bool:
        with Session(self._engine) as session:
            job = self._leased_job(session, job_id, worker_id)
            if job is None:
                return False
            job.status = "completed"
            job.leased_until = None
            job.worker_id = None
            job.error_message = None
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
        with Session(self._engine) as session:
            job = self._leased_job(session, job_id, worker_id)
            if job is None:
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
                job.leased_until = now + timedelta(
                    seconds=(2**job.attempt_count) * backoff_base_seconds
                )
            session.add(job)
            session.commit()
            return True

    def _reclaim(self, session: Session, now: datetime) -> int:
        expired = session.exec(
            select(BackgroundJobRecord)
            .where(
                BackgroundJobRecord.status == "leased",
                col(BackgroundJobRecord.leased_until) <= now,  # pyright: ignore
            )
            .with_for_update(skip_locked=True)
        ).all()
        reclaimed = 0
        for job in expired:
            if self._engine.dialect.name == "postgresql" and job.text_id is not None:
                locked = session.execute(
                    text("SELECT pg_try_advisory_xact_lock(:text_id)"),
                    {"text_id": job.text_id},
                ).scalar()
                if not locked:
                    continue
            reclaimed += 1
            job.worker_id = None
            job.leased_until = None
            job.updated_at = now
            if job.attempt_count >= job.max_retries:
                job.status = "dead_letter"
                job.error_message = "Worker lease expired on final attempt"
                record = session.exec(
                    select(TextRecord).where(
                        TextRecord.id == job.text_id,
                        TextRecord.owner_id == job.owner_id,
                    )
                ).first()
                if record is not None and record.status != "processed":
                    record.status = "failed"
                    record.enrichment_stage = "failed"
                    record.error_message = job.error_message
                    session.add(record)
            else:
                job.status = "pending"
            session.add(job)
        return reclaimed

    def reclaim_expired_leases(self) -> int:
        with Session(self._engine) as session:
            self._lock(session)
            count = self._reclaim(session, utc_now())
            session.commit()
            return count

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
