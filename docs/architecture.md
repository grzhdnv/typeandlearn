# Architecture

## Runtime services

1. `apps/frontend` sends `/api/*` requests through Vite proxy.
2. `apps/backend` exposes `/texts` endpoints.
3. Backend persists text data to SQLite/PostgreSQL via repository layer.
4. Intake/retry/regeneration persist durable jobs; `worker.Worker` alone executes
   enrichment. The API runs an embedded consumer by default; deployments with a
   dedicated worker set `EMBEDDED_WORKER_ENABLED=false`. Both share the same
   transactional claim, heartbeat, and completion path.
5. LLM processing is isolated in `services/llm_service.py`; quota reservations are
   shared through the database.

See [queue acceptance](queue-acceptance-2026-10-20.md) for concurrency verification
and the at-least-once recovery guarantee.

## Backend flow

`route -> service -> repository/llm -> schema`

This keeps HTTP concerns, business logic, and persistence separated.

## Frontend flow

`app shell -> feature APIs -> shared HTTP client -> backend`

Feature modules own UI and orchestration while shared modules own cross-cutting helpers.
