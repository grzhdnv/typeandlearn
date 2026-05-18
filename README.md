# TypeAndLearn

Monorepo-style workspace for the TypeAndLearn app.

## Repository layout

- `apps/backend` — FastAPI API (layered: api/schemas/services/repositories/core)
- `apps/frontend` — SolidJS UI (feature-first structure)
- `packages/shared/contracts` — shared API contract artifacts
- `tests` — repository-level tests and fixtures
- `docs` — architecture and migration documentation
- `archive` — legacy prototypes and historical artifacts

## Quick start

```bash
npm run bootstrap
```

## Run locally

Start backend:

```bash
source .venv/bin/activate
fastapi dev apps/backend/main.py
```

Start frontend:

```bash
npm --prefix apps/frontend run dev
```

## Quality checks

```bash
npm run check
```
