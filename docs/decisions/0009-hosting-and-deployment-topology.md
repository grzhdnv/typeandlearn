# ADR-0009: Deployment Topology and Container Boundaries

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

The v2 prototype executes as two uncontained processes spawned via local bash scripts (`npm run dev:backend` and `npm run dev:frontend`), storing state in local SQLite files. 

Transitioning to staging and production requires a decoupled, containerized infrastructure that isolates CPU-heavy NLP processing from low-latency API request serving, while ensuring local environments reflect production constraints.

## Decision

1. **Service Boundaries & Topology**:
   - **Frontend**: Static SolidJS single-page application compiled to HTML/JS/CSS assets via Vite and served over a global CDN or static host.
   - **API Gateway / Backend**: Stateless FastAPI application container running under Uvicorn behind a reverse proxy (e.g., Traefik or AWS ALB). Handles authentication, HTTP routing, query resolution, and text CRUD.
   - **Background Worker**: Dedicated Python worker container executing the durable queue processor. Runs CPU-intensive spaCy pipelines and upstream LLM requests without starving API event loops.
   - **Database**: Managed PostgreSQL instance with connection pooling (e.g. PgBouncer or SQLAlchemy async pool).

2. **Containerization & Docker Compose**:
   - Containerize the application early (Milestone M1) using multi-stage Dockerfiles.
   - Provide a unified `docker-compose.yml` defining the API, Worker, and PostgreSQL services to eliminate "works on my machine" environmental discrepancies.

3. **Storage Strategy**:
   - PostgreSQL serves as the single source of truth in all shared, staging, and production environments.
   - Local SQLite is restricted exclusively to lightweight, isolated unit tests.

## Consequences

- **Positive**: Strict resource isolation ensures heavy NLP sentence-splitting or LLM stalls never degrade HTTP API latency. Static frontend hosting reduces origin load and infrastructure cost.
- **Negative**: Increases local development complexity by introducing Docker and container networking.
