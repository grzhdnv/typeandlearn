"""HTTP request tracing, correlation ID injection, and access telemetry middleware."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging import current_owner_id, current_request_id
from core.telemetry import record_http_request

logger = logging.getLogger("typeandlearn.access")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """ASGI middleware to capture/generate correlation IDs and emit access telemetry."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract existing incoming correlation ID or generate a new UUID4
        request_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or f"req_{uuid.uuid4().hex[:16]}"
        )
        token_req = current_request_id.set(request_id)

        # Best-effort owner identification from header
        owner_id = request.headers.get("X-Owner-Id") or ""
        token_owner = current_owner_id.set(owner_id)

        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            raise
        finally:
            duration_s = time.perf_counter() - start_time
            latency_ms = round(duration_s * 1000, 2)

            # Record telemetry
            record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_seconds=duration_s,
            )

            # Log request completion with structured extra fields
            logger.info(
                "HTTP %s %s -> %d (%.2fms)",
                request.method,
                request.url.path,
                status_code,
                latency_ms,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "request_id": request_id,
                },
            )

            # Reset context vars
            current_request_id.reset(token_req)
            current_owner_id.reset(token_owner)

        response.headers["X-Request-ID"] = request_id
        return response
