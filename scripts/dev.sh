#!/usr/bin/env bash
# Start both local services and stop both when either exits or Ctrl+C is pressed.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python || ! -f apps/frontend/node_modules/vite/bin/vite.js ]]; then
  echo "Dependencies are missing. Run npm run bootstrap first." >&2
  exit 1
fi

backend_pid=""
frontend_pid=""
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true
  [[ -z "$frontend_pid" ]] || kill "$frontend_pid" 2>/dev/null || true
  [[ -z "$backend_pid" ]] || wait "$backend_pid" 2>/dev/null || true
  [[ -z "$frontend_pid" ]] || wait "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

.venv/bin/python -m uvicorn apps.backend.main:app \
  --host 127.0.0.1 --port 8000 --reload --reload-dir apps/backend &
backend_pid=$!

(
  cd apps/frontend
  exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --strictPort
) &
frontend_pid=$!

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

if ! kill -0 "$backend_pid" 2>/dev/null; then
  wait "$backend_pid"
else
  wait "$frontend_pid"
fi
