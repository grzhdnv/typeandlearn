# Copilot Review & Engineering Instructions for TypeAndLearn

These instructions guide code review, suggestions, and automated checks across the TypeAndLearn codebase.

---

## 1. Core Architectural Boundaries

- **Multi-Tenant Ownership**:
  - Every owned entity table (`texts`, `sentences`, `practice_sessions`, `weak_words`, `background_jobs`, `token_usage_records`) must include non-nullable `owner_id: str`.
  - All repository and service methods must accept and filter by `owner_id`. Never execute queries without owner-scoping.
  - Compound primary/foreign indices must begin with `(owner_id, ...)` for PostgreSQL query performance.

- **Durable Background Processing**:
  - Web API request threads must never perform long-running CPU or LLM tasks directly.
  - Intake persists texts and sentences in a single atomic database transaction and enqueues a `BackgroundJobRecord`.
  - The standalone background worker (`apps/backend/worker.py`) leases work items using concurrent locks (`FOR UPDATE SKIP LOCKED` on PostgreSQL), renews leases with active heartbeats, and reclaims expired leases.

- **Offline Mode & Graceful Degradation**:
  - The application must boot cleanly and serve library browsing and typing practice even when LLM API keys (`GROQ_API_KEY`, `DEEPSEEK_API_KEY`) are missing.
  - If AI enrichment fails or exceeds rate limits, texts remain playable in original typing mode; failures must be truthful and never reported as success.

---

## 2. Privacy & Content Redaction Rules

- **Zero Content Leakage in Logs**:
  - Raw learning text, sentence strings, translations, and prompts must **never** appear in stdout logs or telemetry.
  - Use hashes (`sha256`) and character/token counts instead of raw strings in log metadata.
  - Authorization headers, bearer tokens, API keys (`gsk_*`, `sk-*`), and cookies must be scrubbed automatically by `RedactionFilter`.
  - All logs in production and staging must be single-line structured JSON.

---

## 3. Pure Typing Engine & Frontend Rules

- **State Immutability**:
  - The typing engine core (`apps/frontend/src/features/typing/core/reducer.ts`) is a pure reducer function: `(TypingState, TypingAction) => TypingState`.
  - Do not introduce side effects, DOM manipulations, or timer mutations inside the reducer.
- **Unicode & IME Correctness**:
  - All text comparisons must be normalized to Unicode Normalization Form C (`NFC`).
  - Use grapheme cluster segmentation (`Intl.Segmenter`) to handle multi-byte characters, umlauts, accented ligatures, and emojis correctly.
  - IME composition (`compositionstart`, `compositionupdate`, `compositionend`) must update the composition buffer without registering premature keystroke errors.
- **Vite API Proxying**:
  - All frontend API calls must use relative paths prefixed with `/api/` (e.g. `/api/texts`, `/api/analytics/summary`, `/api/user/export`) to route through the Vite proxy.

---

## 4. Database Migrations (Alembic)

- **Reversible Schema Evolutions**:
  - Every new migration in `apps/backend/alembic/versions/` must implement both `upgrade()` and `downgrade()`.
  - Foreign keys targeting parent tables must specify explicit `ondelete="CASCADE"` where appropriate.
  - Avoid destructive column drops or table renames without staged backwards-compatible deprecation cycles.

---

## 5. Verification & Quality Standards

- **Local Verification Gate**:
  - Run `bash scripts/check.sh` before committing:
    - Python: `uv run ruff check apps/backend tests` and `uv run pyright`.
    - Unit Tests: `uv run python -m unittest discover -s tests/backend -p 'test_*.py'`.
    - Frontend: `npm --prefix apps/frontend run check` and `npm run test:frontend`.
- **End-to-End Testing**:
  - Run `npm run test:e2e` for Playwright browser automation tests covering full user journeys.
