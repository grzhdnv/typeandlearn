# TypeAndLearn Roadmap

This is the authoritative project roadmap. Historical plans are retained under
`archive/plans/` and should not be treated as current requirements.

## Current baseline

The v2 application currently provides:

- A FastAPI and SolidJS monorepo with shared text contracts.
- SQLite or PostgreSQL persistence through SQLModel repositories.
- Text upload, retrieval, metadata editing, deletion, progress, and reset workflows.
- Local sanitization, sentence splitting, spaCy word filtering, and optional LLM filtering.
- LLM-assisted metadata, translation hints, and practice-sentence generation.
- Library browsing, practice navigation, and typing-progress tracking.
- Backend unit tests, Python static checking and compilation, frontend type checking,
  production builds, and CI.

## Next milestone: reliability and test coverage

- [ ] Add backend API integration tests for upload, background processing, CRUD, progress, and regeneration.
- [ ] Add frontend component tests for the library, practice page, and typing interface.
- [ ] Add a Playwright end-to-end test covering text intake through a completed practice session.
- [ ] Build deterministic evaluation fixtures for sanitization, sentence splitting, filtering, translation hints, and generated practice sentences.
- [ ] Add structured request and LLM telemetry with correlation IDs while keeping user text out of logs by default.
- [ ] Define failure and retry behavior for provider rate limits, malformed structured output, and background-processing errors.
- [ ] Adopt an automated Python formatter and incrementally resolve the existing style debt outside behavior changes.

## Product backlog

### Typing practice

- [ ] Benchmark Monkeytype input handling, caret behavior, corrections, and standard WPM and accuracy calculations.
- [ ] Add restart and navigation shortcuts, optional feedback effects, and post-session analytics.
- [ ] Add word-frequency and original-sentence practice modes.

### Language learning

- [ ] Refine on-demand translation hints and feedback for mistakes.
- [ ] Expand language-aware tokenization and lemmatization beyond the current spaCy path.
- [ ] Add configurable difficulty and vocabulary-selection strategies.

### Text intake and library

- [ ] Add validated `.txt` and Markdown file uploads before supporting richer document formats.
- [ ] Improve metadata editing, library filtering, and preloaded practice texts.
- [ ] Define safe handling for unsupported, malformed, and oversized inputs.

### Accounts and progress

- [ ] Design authentication and per-user text ownership.
- [ ] Add durable practice history, accuracy, speed, and vocabulary-progress metrics.
- [ ] Decide how users provide or share LLM credentials in a deployed environment.

### Operations

- [ ] Add database migrations for production schema evolution.
- [ ] Containerize the frontend and backend.
- [ ] Define deployment, observability, backup, and recovery procedures.

## Historical reference

The `legacy/v1` branch and `v1-final` tag preserve the final collaborative v1 state.
The archived planning documents describe earlier implementations and may contain paths
or assumptions that no longer apply to v2.
