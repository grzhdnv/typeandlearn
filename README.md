# TypeAndLearn

TypeAndLearn turns source texts into guided language-learning typing practice. The
current application combines a FastAPI backend, a SolidJS frontend, persistent text
storage, local language processing, and optional LLM-assisted metadata, filtering,
translations, and practice-sentence generation.

## Status

Active v2 application, runnable locally. The M0–M6 milestone plan in
[docs/issue-map.md](docs/issue-map.md) is implemented and verified in-repo: a pure
typing engine with Unicode/grapheme and IME handling, owner-scoped schema with
Alembic migrations, a durable background job queue, Groq-first enrichment with
failover, token spend caps and translation caching, managed-authentication hooks,
durable learning analytics, GDPR/CCPA export and erasure, structured JSON logging
with redaction, hardened CI and staging image builds, WCAG 2.1 AA accessibility,
and automated backup/restore tooling.

`npm run check` passes locally (Ruff, Pyright, 57 backend tests, frontend type
check and production build, 27 frontend tests), alongside Playwright end-to-end,
accessibility, and privacy suites. Enrichment-independent paths run offline without
provider credentials; a `DEEPSEEK_API_KEY` enables live LLM features.

Production promotion is not live yet. The staging workflow builds and smoke-tests
immutable images but does not deploy them to a provisioned environment.

## Repository layout

- `apps/backend` — FastAPI API with routes, schemas, services, repositories, and core configuration
- `apps/frontend` — SolidJS UI organized by feature
- `tests` — repository-level tests and fixtures
- `docs` — current architecture, migration, and roadmap documentation

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Node.js 22 or newer with npm 10 or newer (CI uses Node.js 22)

## Setup

Create the local environment file if it does not already exist:

```bash
cp .env.example .env
```

Set `DEEPSEEK_API_KEY` in `.env` to enable live LLM features, then install the
locked dependencies:

```bash
npm run bootstrap
```

`DATABASE_URL` is optional. When it is unset, the backend uses the ignored local
SQLite database at `apps/backend/data/db.sqlite`. `GROQ_API_KEY` is needed only when
a Groq fallback model is configured. The backend starts without any provider
credentials and serves library, practice, and history in offline mode; only AI
enrichment is disabled. Do not commit `.env`.

Bootstrap installs the pinned spaCy 3.8.0 small pipelines for German, French,
Italian, Spanish, and English from the official
[spaCy model releases](https://github.com/explosion/spacy-models/releases).
They are included in `uv.lock`; no separate model-download command is needed.
Keep spaCy on the compatible 3.8 series until upgrading the models together.

## Run locally

From the repository root, start the backend, background worker, and frontend:

```bash
npm run dev
```

Open [TypeAndLearn](http://127.0.0.1:3000). The backend API docs are at
[localhost:8000/docs](http://localhost:8000/docs). All processes bind to localhost,
reload during development, and stop together on Ctrl+C.

To run them in separate terminals instead:

```bash
npm run dev:backend
.venv/bin/python apps/backend/worker.py
# In another terminal, also from the repository root:
npm run dev:frontend
```

## Quality checks

Run the same backend tests, Python compilation, frontend type checking, and frontend
production build used by CI:

```bash
npm run check
```

The tests use real spaCy pipelines and temporary SQLite databases. Automated API
tests replace external LLM and dictionary calls with fixtures and need no API key.

If text intake reports a missing language model, rerun `npm run bootstrap` and
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

Historical planning documents and v1 code live in git history.

## Legacy v1

The final collaborative coding-club version is preserved at both the `legacy/v1`
branch and the immutable `v1-final` tag:

```bash
git fetch origin --tags
git switch legacy/v1
```
