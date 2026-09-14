# TypeAndLearn Roadmap

This is the authoritative project roadmap. Historical plans live in git history
and should not be treated as current requirements.

The detailed route to private-beta readiness is maintained in
[the production plan](production-plan.md); its M0–M6 milestones are complete per
[the issue map](issue-map.md). Promoting the staged images to a provisioned
environment remains the outstanding production step.

## Current baseline

The v2 application currently provides:

- A FastAPI and SolidJS monorepo with typed API contracts.
- SQLite or PostgreSQL persistence through owner-scoped SQLModel repositories and
  versioned Alembic migrations.
- A durable background job queue with lease heartbeats, retries, and a dedicated
  worker path for spaCy preprocessing.
- Text upload, retrieval, metadata editing, deletion, progress, and reset workflows.
- Local sanitization, sentence splitting, spaCy word filtering, and optional LLM
  filtering.
- Groq-first LLM enrichment with failover, token spend caps, translation caching,
  and truthful job/error UI.
- A pure typing engine with Unicode/grapheme and IME handling, standard WPM and
  accuracy metrics, and post-session results.
- Optional managed authentication, durable practice analytics, and GDPR/CCPA export
  and erasure.
- Structured JSON logging with correlation IDs and content redaction.
- Backend unit tests, Python static checking and compilation, frontend component
  tests, production builds, Playwright E2E/accessibility/privacy suites, CI, and
  staging image builds.

## Completed: reliability and test coverage

These baseline reliability items are complete; the implementation record lives in
[the issue map](issue-map.md).

- [x] Add backend API integration tests for upload, background processing, CRUD, progress, and regeneration (external provider responses use fixtures).
- [x] Pin and install all supported spaCy pipelines during bootstrap, with real-model regression checks.
- [x] Add frontend component tests for the library, practice page, and typing interface.
- [x] Add a Playwright end-to-end test covering text intake through a completed practice session.
- [x] Build deterministic evaluation fixtures for sanitization, sentence splitting, filtering, translation hints, and generated practice sentences.
- [x] Add structured request and LLM telemetry with correlation IDs while keeping user text out of logs by default.
- [x] Define failure and retry behavior for provider rate limits, malformed structured output, and background-processing errors.
- [ ] Adopt an automated Python formatter and incrementally resolve the existing style debt outside behavior changes.

## Product backlog

Items delivered by M0–M6 are marked complete; see [the issue map](issue-map.md) for
the authoritative milestone record.

### Typing practice

- [x] Benchmark Monkeytype input handling, caret behavior, corrections, and standard WPM and accuracy calculations.
- [x] Add restart and navigation shortcuts, optional feedback effects, and post-session analytics.
- [x] Add word-frequency and original-sentence practice modes.

### Language learning

- [ ] Refine on-demand translation hints and feedback for mistakes.
- [ ] Expand language-aware tokenization and lemmatization beyond the current spaCy path.
- [ ] Add configurable difficulty and vocabulary-selection strategies.

### Text intake and library

- [ ] Add validated `.txt` and Markdown file uploads before supporting richer document formats.
- [ ] Improve metadata editing, library filtering, and preloaded practice texts.
- [ ] Define safe handling for unsupported, malformed, and oversized inputs.

### Accounts and progress

- [x] Design authentication and per-user text ownership.
- [x] Add durable practice history, accuracy, speed, and vocabulary-progress metrics.
- [ ] Decide how users provide or share LLM credentials in a deployed environment.

### Operations

- [x] Add database migrations for production schema evolution.
- [x] Containerize the frontend and backend.
- [x] Define deployment, observability, backup, and recovery procedures.

## Historical reference

The `legacy/v1` branch and `v1-final` tag preserve the final collaborative v1 state.
Older planning documents in git history describe earlier implementations and may
contain paths or assumptions that no longer apply to v2.
