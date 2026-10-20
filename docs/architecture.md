# Architecture

## Runtime services

1. `apps/frontend` sends `/api/*` requests through Vite proxy.
2. `apps/backend` exposes `/texts` endpoints.
3. Backend persists text data to SQLite/PostgreSQL via repository layer.
4. Intake atomically persists source text, preparation options, and a durable job
   before doing NLP or provider work. The worker saves stable sentence preparation,
   metadata and vocabulary checkpoints; original practice can begin before optional
   metadata/enrichment completes when a language was provided.
5. Intake/retry/regeneration persist durable jobs; `worker.Worker` alone executes
   enrichment. The API runs an embedded consumer by default; deployments with a
   dedicated worker set `EMBEDDED_WORKER_ENABLED=false`. Both share the same
   transactional claim, heartbeat, and completion path.
6. LLM processing is isolated in `services/llm_service.py`; quota reservations are
   shared through the database.

See [queue acceptance](queue-acceptance-2026-10-20.md) for concurrency verification
and the at-least-once recovery guarantee. [Background intake acceptance](intake-acceptance-2026-10-20.md)
covers source persistence, preparation UI, metadata/progress concurrency, and rollback.

## Backend flow

`route -> service -> repository/llm -> schema`

This keeps HTTP concerns, business logic, and persistence separated.

## Frontend flow

`app shell -> feature APIs -> shared HTTP client -> backend`

Feature modules own UI and orchestration while shared modules own cross-cutting helpers.
