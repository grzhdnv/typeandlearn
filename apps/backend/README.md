# TypeAndLearn Backend

FastAPI backend with explicit application layers:

- `api/routes` — HTTP route handlers
- `schemas` — request/response and domain schema models
- `services` — business logic and LLM integration
- `repositories` — storage adapters
- `core` — settings and app configuration

## Run

From repo root:

```bash
source .venv/bin/activate
fastapi dev apps/backend/main.py
```

## Data and prompt files

- `apps/backend/data/db.json`
- `apps/backend/prompts/text_to_db.md`
