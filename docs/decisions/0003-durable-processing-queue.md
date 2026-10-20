# ADR-0003: PostgreSQL-Backed Transactional Processing Queue

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

The prototype processes text intake (NLP tokenization, spaCy sentence splitting, dictionary lookups, and LLM translations) using FastAPI in-memory `BackgroundTasks`. 

This approach has critical production vulnerabilities:
- Process termination or pod restarts silently drop active and queued jobs.
- There are no retry budgets, dead-letter storage, or failure backoffs.
- A failed enrichment step can leave a text permanently in `processing` or mark it `processed` despite missing translations.
- Introducing a distributed message broker (such as Redis, RabbitMQ, or Celery) adds operational complexity, another point of failure, and multi-service synchronization overhead.

## Decision

1. **Transactional PostgreSQL Job Table**:
   - Implement a durable `background_jobs` table in PostgreSQL.
   - Enqueue jobs within the same database transaction as the initial text intake to ensure zero loss of enqueued tasks.

2. **Concurrency Control via `FOR UPDATE SKIP LOCKED`**:
   - Worker processes query for pending jobs using `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1`.
   - Jobs are assigned a lease expiration timestamp (`leased_until`). Workers periodically issue heartbeat updates to extend the lease during long-running enrichment.

3. **Crash Recovery & Dead-Letter Handling**:
   - Jobs with expired leases are automatically unlocked and made eligible for pickup by other workers.
   - Jobs track `attempt_count` with exponential backoff.
   - If `attempt_count >= MAX_RETRIES` (default 3), the job transitions to `dead_letter` status and records structured error diagnostics.
   - Texts associated with terminal failures reflect a clear `failed` state in the UI rather than hanging indefinitely.

4. **Deferred Infrastructure**:
   - Defer separate queue brokers (e.g., Redis / Celery) until throughput metrics demonstrate that transactional database locking constitutes a database bottleneck.

## Consequences

- **Positive**: Complete transactional consistency between application records and background jobs. Zero dropped tasks on server restart. No extra broker infrastructure to deploy or monitor.
- **Negative**: Workers poll the database at a modest cadence, generating baseline read traffic on PostgreSQL.

## Implementation verified on 20 October 2026

API upload/retry/regeneration now persist queue work without scheduling direct
`BackgroundTasks`. The API lifespan runs the same `Worker` consumer as the CLI by
default; `EMBEDDED_WORKER_ENABLED=false` delegates consumption to dedicated workers
(as configured in Docker Compose). Startup resumes the queue across all owners.

SQLite claims acquire `BEGIN IMMEDIATE` before reading candidates. PostgreSQL
retains `FOR UPDATE SKIP LOCKED`; per-text advisory locks serialize claim/requeue
and recovery for legacy duplicate job records. Retry and regeneration commit text
state, replacement frequencies, and the queue change together. Pending requests
reuse existing work; a leased job rejects requeue. Manual retries preserve an
existing job's attempt budget. Terminal jobs require an explicit new retry.

Only the consumer holding the unexpired, unique lease token can renew, complete,
or fail its specific job. Heartbeats run through graceful shutdown and are joined
when execution finishes. Expired final attempts become dead letters and mark the
owned text failed. The enrichment service checks lease ownership around provider
calls and persistence boundaries and never completes other jobs for that text.

The delivery guarantee is **at least once**, not exactly once: a crash after a
provider request can cause another request during recovery. Cooperative lease
checks reject late responses at the next checkpoint; they are not a distributed
transaction with an external provider. Existing sentence/cache persistence limits
repeated work. Live PostgreSQL locking/recovery still needs staging acceptance.
See [SQLite and process verification](../queue-acceptance-2026-10-20.md).
