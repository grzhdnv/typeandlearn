# Durable queue acceptance — 20 October 2026

The API and standalone worker now execute enrichment through one durable queue.
Request handlers no longer start enrichment directly, and startup no longer scans
one owner's texts to spawn independent processing threads.

## Runtime behavior

- Local API: one embedded `Worker` starts during lifespan and resumes queued work
  for every owner. Shutdown waits for active work while its heartbeat continues.
- Dedicated workers: set `EMBEDDED_WORKER_ENABLED=false` on the API and start
  `.venv/bin/python apps/backend/worker.py` with the same database/provider settings.
  Docker Compose already selects this arrangement.
- SQLite uses `BEGIN IMMEDIATE` before selecting jobs. PostgreSQL uses locked rows
  with `SKIP LOCKED` and per-text transaction advisory locks. Distinct legacy jobs
  for a text cannot be leased together through this path.
- Retry and regeneration atomically update text state, word frequencies when
  applicable, and queue work. Pending work is reused; leased work is rejected.
- Each claim has a fresh lease token, even when worker IDs are reused. Completion,
  failure, and renewal require a matching unexpired lease. The text service never
  finishes other jobs. Expired final attempts become dead letters with failed text
  state; automatic retries retain their attempt budget and exponential backoff.
- Progress logs use IDs and counts rather than source text, translations, or seed
  words. Worker failure diagnostics store the exception class rather than upstream
  exception strings that could contain content.

## Verification

`npm run check` passed: Ruff, Pyright, compilation, **112 backend tests**, frontend
build/types, and **31 frontend unit tests**. **27 Chromium tests** passed against
isolated temporary services with all provider keys disabled.

New regression cases cover:

- Twelve simultaneous SQLite claimers and six jobs: every job claimed once.
- Legacy duplicate jobs for a single text: only one active lease.
- Rejection of pending/completed/stale-worker terminal updates and expired renewal.
- Final crashed attempts becoming dead letters and exposing failed text state.
- Heartbeats keeping a slow job leased beyond its initial duration.
- Real HTTP upload returning queued work before enrichment; two consumers and
  repeated pending/leased retry/regeneration requests without duplicate execution.
- A fresh API lifespan resuming another owner's durable job.
- Lease expiry while a provider call is in flight: the replacement completes, and
  the old response cannot overwrite the saved translation or fail the completed job,
  including when both workers use the same configured ID.

An additional process smoke test started a real isolated Uvicorn API with embedded
consumption disabled, uploaded a synthetic German sentence, and started two actual
CLI worker processes. Exactly one attempt was recorded. Without provider keys the
text became truthfully failed, its original sentence remained available, and both
workers exited cleanly on SIGTERM. No live inference or paid spend was needed.

Existing SQLite unclosed-connection ResourceWarnings remain a separate finding.

## Limits and next work

Delivery is **at least once**. A crash after dispatching an external request can
require another request after lease expiry. Ownership checks are cooperative
checkpoints, not a distributed transaction spanning database writes and providers.
A forced process stop releases work only after lease expiration; graceful shutdown
drains the active job. Completed translations and caches reduce recovery work.

SQLite concurrency and API/process flows were exercised locally. Live PostgreSQL
locking, migrations, and recovery are still a staging acceptance gate; PostgreSQL
was not available on this host. No schema migration is introduced by this change.

Intake still performs local preprocessing and optional AI metadata/filtering before
responding. Moving those operations onto durable jobs is the next engineering task.
