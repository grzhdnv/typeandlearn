# TypeAndLearn

TypeAndLearn turns source texts into guided language-learning typing practice. The
current application combines a FastAPI backend, a SolidJS frontend, persistent text
storage, local language processing, and optional LLM-assisted metadata, filtering,
translations, and practice-sentence generation.

## Status

Active local v2 prototype. Local repairs verified on 19 October 2026: text intake,
metadata editing, original and generated practice navigation, reset, saved progress,
results, and history. The current checks cover 121 backend tests, 32 frontend unit
tests, and 29 Chromium browser regressions. A live synthetic comparison verified
five languages, metadata, generated exercises, and real DeepSeek fallback.

Absent author/category values are normalized on intake, inference, edits and API
readback, including legacy serialized nulls. Clearing either field is persisted;
explicit edits remain protected from later inference.

Core library and original-text practice work without provider credentials when a
supported language is selected during intake. Automatic metadata, translations,
and generated drills require a configured provider; failures remain visible while
the original text stays available.

Owner-scoped data, JWT backend support, a job queue, and analytics are implemented,
but this remains a local development app. API intake, retry, and regeneration now
use one durable queue consumed by the local embedded worker or standalone workers.
Upload saves the source and job before any NLP or provider work; preparation and
metadata/filtering run in the worker with durable checkpoints.
SQLite and PostgreSQL 18.6 concurrency, lease loss, crash budgets, and recovery
across owners are tested locally. PostgreSQL startup migrations now serialize
across API/workers and accept the existing long revision IDs.
The staging workflow
builds and smoke-tests containers without deploying a hosted service. Private-beta
security, cross-browser/accessibility, recovery, and deployment acceptance remain
unfinished. See [the roadmap](docs/roadmap.md).

The OpenRouter free-only comparison completed on 20 October: Ultra 550B and Dots
280B completed all seven final tasks with reasoning disabled; Super 120B returned
upstream 404s. A MiniMax M3.1 Flash follow-up passed 7/7 using prompted JSON output
and mandatory low-effort reasoning. MiniMax is the leading free challenger in this
small sample, with Ultra as an alternative. A subsequent five-language technical
acceptance pass saved ten translations and 25 drills with no missing UI hints;
see [acceptance and content-use scope](docs/minimax-acceptance-2026-10-20.md). MiniMax
was activated in the local profile with user approval: Groq → MiniMax → capped
DeepSeek. CEFR estimates/exercise style still need review. Repository defaults
remain Groq/DeepSeek. See the
[evaluation report](docs/openrouter-evaluation-2026-10-20.md) and
[session handoff](HANDOFF.md). Local PostgreSQL 18
acceptance now passes; reproduce recovery on protected staging, improve CEFR/exercise
quality, and expand realistic multilingual practice coverage before private beta.

## Repository layout

- `apps/backend` — FastAPI API with routes, schemas, services, repositories, and core configuration
- `apps/frontend` — SolidJS UI organized by feature
- `packages/shared/contracts` — shared API contract artifacts
- `tests` — repository-level tests and fixtures
- `docs` — current architecture, migration, and roadmap documentation
- `archive` — historical plans, prototypes, v1 code, and migration data

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Node.js 22 or newer with npm 10 or newer (CI uses Node.js 22)

## Setup

Create the local environment file if it does not already exist:

```bash
cp .env.example .env
```

For AI features, set `GROQ_API_KEY` and/or `DEEPSEEK_API_KEY` in `.env`.
Install the locked dependencies:

```bash
npm run bootstrap
```

`DATABASE_URL` is optional. When it is unset, the backend uses the ignored local
SQLite database at `apps/backend/data/db.sqlite`. The default provider order is Groq `openai/gpt-oss-120b`, then DeepSeek
`deepseek-flash` with thinking disabled when its key is available. DeepSeek is capped
at the approved $0.50/day and $5/month across processes sharing this database.
Quota reservations, reset headers, bounded repair, and actual-model usage accounting
apply to every enrichment task. See [provider policy](docs/decisions/0005-llm-routing-and-spend.md)
and [the live synthetic comparison](docs/provider-evaluation-2026-10-19.md).
All limits and price estimates are documented in `.env.example`.

Provider credentials are optional for library access and original-text practice.
Select German, French, Italian, Spanish, or English when adding text without AI.
Do not commit `.env`.

Bootstrap installs the pinned spaCy 3.8.0 small pipelines for German, French,
Italian, Spanish, and English from the official
[spaCy model releases](https://github.com/explosion/spacy-models/releases).
They are included in `uv.lock`; no separate model-download command is needed.
Keep spaCy on the compatible 3.8 series until upgrading the models together.

## Run locally

From the repository root, start both services:

```bash
npm run dev
```

Open [TypeAndLearn](http://127.0.0.1:3000). The backend API docs are at
[localhost:8000/docs](http://127.0.0.1:8000/docs). Both services bind to localhost,
reload during development, and stop together on Ctrl+C.

The API starts one queue consumer by default, so local enrichment needs no extra
terminal. To use dedicated workers, set `EMBEDDED_WORKER_ENABLED=false` for the API
and run `.venv/bin/python apps/backend/worker.py` against the same database and
provider settings. Docker Compose uses this dedicated-worker arrangement.
Both modes use identical leases and heartbeats; shutdown drains the active job.
See [queue verification and recovery limits](docs/queue-acceptance-2026-10-20.md)
and [background intake acceptance](docs/intake-acceptance-2026-10-20.md).
While preparation runs, the practice page shows a saved-source preview. With an
explicit language, original practice becomes available after local sentence
preparation, before optional metadata and AI enrichment finish.

To run them in separate terminals instead:

```bash
npm run dev:backend
# In another terminal, also from the repository root:
npm run dev:frontend
```

## PostgreSQL development

Compose uses pinned PostgreSQL 18.6 with a new `postgres18_data` volume mounted at
`/var/lib/postgresql`. Existing PostgreSQL 16 volumes are separate; starting the
new volume creates a fresh database. The local `npm run dev` flow still defaults
to SQLite unless `DATABASE_URL` selects PostgreSQL. See the
[PostgreSQL acceptance and upgrade notes](docs/postgresql-acceptance-2026-10-21.md)
for the 10 live tests, startup repair, synthetic 16-to-18 rehearsal and remaining
staging gates.

## Quality checks

Run the same backend tests, Python compilation, frontend type checking, and frontend
production build used by CI:

```bash
npm run check
npm run test:e2e
```

Browser tests start isolated services on ports 13000/18000, use a temporary
SQLite database, and disable provider keys; they never reuse the personal library
or development servers. Backend tests use real spaCy pipelines and temporary SQLite databases. Automated API
tests replace external LLM and dictionary calls with fixtures and need no API key.

If background text preparation reports a missing language model, rerun `npm run bootstrap` and
restart the backend. If ports 3000 or 8000 are occupied, stop the other local server
before starting this one.

## Project documentation

- [Roadmap](docs/roadmap.md) — authoritative current backlog and completed baseline
- [Production plan](docs/production-plan.md) — production architecture, Monkeytype
  lessons, LLM policy, quality gates, delivery sequence, and launch criteria
- [Architecture Decision Records (ADRs)](docs/decisions/index.md) — foundational
  engineering and design decisions (ADRs 0001–0009)
- [Typing Behavior Specification](docs/behavior-spec.md) — authoritative input handling,
  state machine, and metric calculation rules
- [Milestone & Issue Map](docs/issue-map.md) — actionable issue tracking for M1–M6
- [Architecture](docs/architecture.md) — runtime services and code boundaries
- [Data flow working map](docs/data-flow.md) — editable, layered current and target
  application flows with annotation prompts
- [Migration guide](docs/migration-guide.md) — v1-to-v2 path and command changes

Historical planning documents remain available under `archive/plans/` for context;
they are not the current backlog.

## Legacy v1

The final collaborative coding-club version is preserved at both the `legacy/v1`
branch and the immutable `v1-final` tag:

```bash
git fetch origin --tags
git switch legacy/v1
```
