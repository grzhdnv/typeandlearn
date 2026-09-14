#!/usr/bin/env bash
# Run the backend API plus its durable worker for Playwright E2E runs.
set -euo pipefail

cd "$(dirname "$0")/.."

uv run --locked python apps/backend/worker.py &
worker_pid=$!
cleanup() {
  kill "$worker_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run --locked fastapi dev apps/backend/main.py --port 8000 --host 127.0.0.1
