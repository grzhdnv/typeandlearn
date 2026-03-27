# Add DB Plan (SQLite First)

## 1. Install DB packages
From project root:

```bash
uv add sqlmodel sqlalchemy alembic
```

## 2. Add SQLite + models in backend/main.py
- Configure engine: `sqlite:///./typeandlearn.db`
- Add SQLModel table for translations:
  - `id` (PK)
  - `foreign_sentence` (str)
  - `native_sentence` (str)
  - `alignment` (JSON)
- Add `get_session()` dependency.

## 3. Create tables on startup
- In FastAPI startup event: `SQLModel.metadata.create_all(engine)`

## 4. Add CRUD endpoints
Keep existing test endpoint:
- `GET /translation` (current message endpoint)

Add DB endpoints:
- `POST /translations` create row
- `GET /translations` list rows
- `GET /translations/{translation_id}` get one row

## 5. Run backend
```bash
fastapi dev backend/main.py
```

## 6. Keep frontend call pattern
Use Vite proxy and call backend through `/api/*` from frontend.
Example:
- `fetch('/api/translation')` for existing test route
- `fetch('/api/translations')` for DB list route

## 7. Quick verify
Create one row:

```bash
curl -X POST http://127.0.0.1:8000/translations \
  -H "Content-Type: application/json" \
  -d '{
    "foreign_sentence": "J\'aime les pommes rouges.",
    "native_sentence": "I like the red apples.",
    "alignment": [
      { "f": [0], "n": [0, 1] },
      { "f": [1], "n": [2] },
      { "f": [2], "n": [4] },
      { "f": [3], "n": [3] }
    ]
  }'
```

List rows:

```bash
curl http://127.0.0.1:8000/translations
```
