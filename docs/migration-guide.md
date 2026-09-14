# Migration Guide

## Major path changes

- `backend/*` -> `apps/backend/*`
- `frontend/*` -> `apps/frontend/*`
- `test_files/*` -> `tests/fixtures/raw/*`
- `typeandlearn/*` -> `archive/legacy/typeandlearn-cli/*`
- `plan/*` -> `docs/plans/*`

## Command changes

- Backend dev server: `fastapi dev apps/backend/main.py`
- Frontend dev server: `npm --prefix apps/frontend run dev`
- Workspace checks: `npm run check`
- Workspace bootstrap: `npm run bootstrap`

## Notes

The backend API surface remains `/texts`-based for compatibility with the existing frontend flow.
