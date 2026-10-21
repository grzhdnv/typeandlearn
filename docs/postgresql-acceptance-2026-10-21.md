# PostgreSQL 18 acceptance — 21 October 2026

TypeAndLearn's Compose database now uses PostgreSQL **18.6**. The image is pinned
to the multi-architecture index digest
`sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`
(`postgres:18.6-alpine`; amd64 and arm64 variants are present). This matches the
approved native PostgreSQL 18.6 tools. No dependency or shared-toolchain change
was needed in this project.

## Database startup repair

The first live PostgreSQL run failed while recording revision
`0002_translation_cache_and_token_usage`: Alembic's default `VARCHAR(32)` version
column is too short. SQLite did not enforce this limit. Existing revision IDs
remain unchanged; the PostgreSQL migration environment now creates or widens its
version column to 128 characters before running revisions.

The same transaction takes advisory lock `76239403` before version-table discovery
and holds it through the migration commit. API, worker and migration CLI startup
therefore serialize their DDL and version updates. The provider-ledger lock is a
separate key. A failed migration rolls back its PostgreSQL transaction. SQLite
migration and browser regressions still pass after the transaction change.

## Verified locally

The opt-in suite in `tests/postgresql/test_postgresql.py` passed **10 tests** on the
actual PostgreSQL 18.6 container, with real SQLAlchemy/psycopg connections and all
provider keys disabled. It verifies:

- Populated upgrade from `0005_provider_governance`, repeatable head upgrade, guarded
  rollback of unprepared sources and source-preserving rollback/re-upgrade.
- Existing ORM schema adoption, including an empty legacy 32-character version table.
- Six independent concurrent migration-startup interpreters reaching the same head.
- Sixteen claimers for eight jobs, and concurrent legacy duplicate jobs for one text.
- Stale-owner completion/failure rejection, expired renewal, final-crash dead letters,
  failed text state and attempt budgets.
- Heartbeat renewal past the original lease, leased retry rejection and eight
  concurrent requeues producing a single pending job.
- Concurrent provider-ledger reservations respecting the shared request ceiling,
  without making provider requests.
- API lifespan consumption of another owner's queued source while HTTP ownership
  checks deny that record to the default owner.
- Real HTTP upload through Uvicorn plus two actual CLI workers, with one claim,
  background sentence preparation, truthful offline failure and preserved source.
  Shutdown verifies both worker exit codes and completed API lifespan cleanup;
  Uvicorn then intentionally re-raises SIGTERM.
- Abrupt process exit after the real preparation commit, followed by replacement
  consumption preserving sentence IDs, completion progress and source text.

Each test uses a fresh randomly named schema in a disposable database named
`typeandlearn_acceptance` and drops only that schema. Other database names are
rejected. Subprocesses override the application database and blank all provider keys.
The suite is opt-in locally and has a dedicated PostgreSQL 18 CI service/job; the
CI runs on [draft PR #20](https://github.com/grzhdnv/typeandlearn/pull/20); use
its latest checks for remote status. The initial run exposed an unsupported FIFO
assertion in the duplicate-job test. The corrected test accepts either winner
while still requiring a single active lease and then claiming the remaining job.

```sh
TYPEANDLEARN_TEST_POSTGRES_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/typeandlearn_acceptance' \
DATABASE_URL=sqlite:// GROQ_API_KEY= OPENROUTER_API_KEY= DEEPSEEK_API_KEY= \
EMBEDDED_WORKER_ENABLED=false \
.venv/bin/python -m unittest discover -s tests/postgresql -v
```

Separate checks exercised the actual Compose service with an isolated project,
volume and loopback port. A committed SQL probe survived stop/start at the expected
`/var/lib/postgresql/18/docker` data directory. Compose configuration validation
passed. The acceptance resources were removed after verification.

A synthetic PostgreSQL 16 prior-schema database was also dumped with the approved
18.6 `pg_dump`, restored into a separate 18.6 database with `pg_restore`, and migrated
to head. Sentence text, translation, owner and completion progress survived. This
was a disposable rehearsal, not a migration of the personal development database.

`npm run check` passed **121 backend / 32 frontend tests**, Ruff, Pyright, Python
compilation, frontend types and production build. **29 Chromium tests** passed.
Existing SQLite unclosed-connection ResourceWarnings remain a separate finding.

## Fresh development and existing volumes

Compose now mounts a new `postgres18_data` volume at `/var/lib/postgresql`, as
required by the official 18+ image layout. The prior `postgres_data` volume is not
reused or deleted. New development can start with an empty PostgreSQL 18 database;
there is currently no valuable application data requiring migration. No learning
schema redesign was needed for this upgrade. Native `npm run dev` still defaults
to SQLite unless `DATABASE_URL` explicitly selects PostgreSQL.

An existing PostgreSQL 16 data directory cannot be mounted directly into 18. To
retain one, use a separately tested logical dump/restore or `pg_upgrade` plan.
Never use `docker compose down --volumes` as an upgrade step against a wanted
library. Starting the new volume does not itself copy old data.

References: [official image data layout](https://hub.docker.com/_/postgres) and
[PostgreSQL major-version upgrades](https://www.postgresql.org/docs/18/upgrading.html).

## Remaining acceptance

This establishes local PostgreSQL 18 behavior, not hosted staging readiness or
exactly-once delivery. Protected staging deployment, previous-application-version
compatibility, operational backup/restore tooling and permissions, outages/load,
security/authentication and browser/accessibility acceptance remain open. Lease
checks remain cooperative; an external request may repeat after a process crash.
CEFR grading and exercise naturalness remain the next product-quality work.
