"""API route for Prometheus-compatible telemetry and operational metrics."""

from typing import Dict

from fastapi import APIRouter, Response
from sqlmodel import Session, col, func, select

from core.database import engine
from core.telemetry import format_prometheus_metrics
from models.cache import TokenUsageRecord
from models.jobs import BackgroundJobRecord

router = APIRouter(tags=["telemetry"])


@router.get("/metrics")
def get_metrics() -> Response:
    """Return Prometheus-formatted operational telemetry and background queue metrics."""
    extra_metrics: Dict[str, object] = {
        "typeandlearn_app_info{version=\"1.0.0\"}": 1,
    }

    try:
        with Session(engine) as session:
            # 1. Database connection probe
            extra_metrics["typeandlearn_database_connected"] = 1

            # 2. Queue job counts by status
            job_counts = session.exec(
                select(BackgroundJobRecord.status, func.count(col(BackgroundJobRecord.id)))
                .group_by(BackgroundJobRecord.status)
            ).all()

            for status_name, count in job_counts:
                extra_metrics[f'typeandlearn_background_jobs{{status="{status_name}"}}'] = count

            # 3. Aggregate token usage
            total_tokens = session.exec(select(func.sum(col(TokenUsageRecord.total_tokens)))).one() or 0
            extra_metrics["typeandlearn_tokens_consumed_total"] = total_tokens
    except Exception:
        extra_metrics["typeandlearn_database_connected"] = 0

    content = format_prometheus_metrics(extra_metrics)
    return Response(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
