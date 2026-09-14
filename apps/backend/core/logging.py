"""Structured JSON logging with correlation ID tracing and automated privacy redaction."""

from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from typing import Any, Dict

from core.settings import settings

# Thread-safe and async-safe request context variables
current_request_id: ContextVar[str] = ContextVar("current_request_id", default="")
current_owner_id: ContextVar[str] = ContextVar("current_owner_id", default="")

# Standard LogRecord attributes to ignore when harvesting extra custom attributes
_STANDARD_LOG_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
}

# Regex patterns for sensitive tokens and credentials
_CREDENTIAL_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", re.IGNORECASE), "Bearer [REDACTED_JWT]"),
    (re.compile(r"gsk_[a-zA-Z0-9_-]{10,}", re.IGNORECASE), "[REDACTED_GROQ_KEY]"),
    (re.compile(r"sk-[a-zA-Z0-9_-]{10,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)(password|secret|token|api_key|authorization)=([^\s&]+)"), r"\1=[REDACTED]"),
]

# Sensitive keys that should not be logged in raw form in log record extras
_SENSITIVE_CONTENT_KEYS = {
    "raw_text",
    "sentence_text",
    "original_text",
    "translation",
    "prompt",
    "prompt_text",
    "password",
    "secret",
    "api_key",
    "token",
    "authorization",
    "cookie",
}


def redact_sensitive_string(value: str) -> str:
    """Scrub tokens, API keys, and authorization headers from string text."""
    redacted = value
    for pattern, replacement in _CREDENTIAL_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def sanitize_content_value(key: str, value: Any) -> Any:
    """Sanitize individual fields, replacing raw user text with hashes and lengths."""
    lowered = key.lower()
    if lowered in _SENSITIVE_CONTENT_KEYS:
        if isinstance(value, str):
            if lowered in {"password", "secret", "api_key", "token", "authorization", "cookie"}:
                return "[REDACTED]"
            content_hash = hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]
            return f"[REDACTED_CONTENT: sha256={content_hash}, len={len(value)}]"
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_sensitive_string(value)
    return value


class RedactionFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials and user text from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_string(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_content_value(k, v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                sanitized_args = []
                for item in record.args:
                    if isinstance(item, str):
                        sanitized_args.append(redact_sensitive_string(item))
                    else:
                        sanitized_args.append(item)
                record.args = tuple(sanitized_args)

        return True


class JSONFormatter(logging.Formatter):
    """Standardized single-line JSON log formatter with correlation ID enrichment."""

    def format(self, record: logging.LogRecord) -> str:
        # Generate message with record.args safely interpolated
        message = record.getMessage()
        message = redact_sensitive_string(message)

        # Context correlation
        request_id = getattr(record, "request_id", None) or current_request_id.get() or None
        owner_id = getattr(record, "owner_id", None) or current_owner_id.get() or None

        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "environment": settings.environment,
            "service": settings.service_name,
        }

        if request_id:
            payload["request_id"] = request_id
        if owner_id:
            payload["owner_id"] = owner_id

        # Attach custom extra fields attached to the LogRecord
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and key not in payload:
                payload[key] = sanitize_content_value(key, value)

        # Include exception trace if present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    log_format: str | None = None,
    log_level: str | None = None,
) -> None:
    """Configure root and framework loggers with JSON formatting and privacy redaction."""
    fmt = (log_format or settings.log_format).lower()
    lvl_name = (log_level or settings.log_level).upper()
    level = getattr(logging, lvl_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicate log lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.addFilter(RedactionFilter())

    if fmt == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        plain_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
        console_handler.setFormatter(logging.Formatter(plain_format))

    root_logger.addHandler(console_handler)

    # Reconfigure uvicorn loggers to inherit the root handler
    for uvicorn_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        u_logger = logging.getLogger(uvicorn_name)
        u_logger.handlers = []
        u_logger.propagate = True
