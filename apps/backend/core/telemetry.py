"""In-memory telemetry and Prometheus metrics collector."""

from collections import defaultdict
import threading
from typing import Any, Dict, Tuple

_lock = threading.Lock()

# Counter metrics: (method, path_group, status_code) -> count
_http_requests_total: Dict[Tuple[str, str, int], int] = defaultdict(int)

# Latency metrics: (method, path_group) -> (sum_duration_seconds, count)
_http_request_duration_sum: Dict[Tuple[str, str], float] = defaultdict(float)
_http_request_duration_count: Dict[Tuple[str, str], int] = defaultdict(int)


def _group_path(path: str) -> str:
    """Normalize dynamic URL segments to prevent high-cardinality metric explosion."""
    parts = path.strip("/").split("/")
    grouped = []
    for part in parts:
        if part.isdigit():
            grouped.append(":id")
        elif len(part) > 20 and all(c in "0123456789abcdefABCDEF-" for c in part):
            grouped.append(":uuid")
        else:
            grouped.append(part)
    return "/" + "/".join(grouped) if grouped else "/"


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """Record execution latency and response code for an HTTP request."""
    grouped = _group_path(path)
    with _lock:
        _http_requests_total[(method, grouped, status_code)] += 1
        _http_request_duration_sum[(method, grouped)] += duration_seconds
        _http_request_duration_count[(method, grouped)] += 1


def format_prometheus_metrics(extra_metrics: Dict[str, Any] | None = None) -> str:
    """Format recorded telemetry in standard Prometheus text representation."""
    lines = [
        "# HELP typeandlearn_http_requests_total Total number of HTTP requests processed",
        "# TYPE typeandlearn_http_requests_total counter",
    ]

    with _lock:
        for (method, path, status), count in sorted(_http_requests_total.items()):
            lines.append(
                f'typeandlearn_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        lines.extend([
            "# HELP typeandlearn_http_request_duration_seconds Latency of HTTP requests in seconds",
            "# TYPE typeandlearn_http_request_duration_seconds summary",
        ])
        for (method, path), total_s in sorted(_http_request_duration_sum.items()):
            count = _http_request_duration_count[(method, path)]
            lines.append(
                f'typeandlearn_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {round(total_s, 5)}'
            )
            lines.append(
                f'typeandlearn_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
            )

    if extra_metrics:
        for key, value in extra_metrics.items():
            if isinstance(value, (int, float)):
                lines.append(f"{key} {value}")
            elif isinstance(value, dict):
                for label, val in value.items():
                    if isinstance(val, (int, float)):
                        lines.append(f'{key}{{target="{label}"}} {val}')

    return "\n".join(lines) + "\n"
