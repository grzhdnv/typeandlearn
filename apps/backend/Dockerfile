# Multi-stage build for TypeAndLearn FastAPI backend
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install locked Python dependencies including pinned spaCy models
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY apps/backend ./apps/backend

# Runtime stage
FROM python:3.14-slim AS runner

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/apps/backend /app/apps/backend
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

CMD ["fastapi", "run", "apps/backend/main.py", "--port", "8000", "--host", "0.0.0.0"]
