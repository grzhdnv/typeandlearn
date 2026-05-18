# Architecture

## Runtime services

1. `apps/frontend` sends `/api/*` requests through Vite proxy.
2. `apps/backend` exposes `/texts` endpoints.
3. Backend persists text data to JSON via repository layer.
4. LLM processing is isolated in `services/llm_service.py`.

## Backend flow

`route -> service -> repository/llm -> schema`

This keeps HTTP concerns, business logic, and persistence separated.

## Frontend flow

`app shell -> feature APIs -> shared HTTP client -> backend`

Feature modules own UI and orchestration while shared modules own cross-cutting helpers.
