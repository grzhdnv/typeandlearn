# TypeAndLearn

TypeAndLearn turns source texts into guided language-learning typing practice. The
current application combines a FastAPI backend, a SolidJS frontend, persistent text
storage, local language processing, and optional LLM-assisted metadata, filtering,
translations, and practice-sentence generation.

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
- Node.js 22 with npm

## Setup

Create the local environment file and add a DeepSeek API key when using LLM-backed
features:

```bash
cp .env.example .env
npm run bootstrap
```

`DATABASE_URL` is optional. When it is unset, the backend uses the ignored local
SQLite database at `apps/backend/data/db.sqlite`. `GROQ_API_KEY` is needed only when
a Groq fallback model is configured.

## Run locally

Start the backend:

```bash
source .venv/bin/activate
fastapi dev apps/backend/main.py
```

Start the frontend in another terminal:

```bash
npm --prefix apps/frontend run dev
```

## Quality checks

Run the same backend tests, Python compilation, frontend type checking, and frontend
production build used by CI:

```bash
npm run check
```

## Project documentation

- [Roadmap](docs/roadmap.md) — authoritative current backlog and completed baseline
- [Architecture](docs/architecture.md) — runtime services and code boundaries
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
