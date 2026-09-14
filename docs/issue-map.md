# TypeAndLearn Issue & Milestone Map

This issue map translates the production plan into discrete, reviewable engineering milestones and tasks.

---

## Milestone M0 — Decisions, Specifications & Honest Prototype UI (Complete)

- **[x] ISSUE-001**: Author foundational Architecture Decision Records (ADRs 0001–0009).
- **[x] ISSUE-002**: Draft authoritative Typing Engine Behavior Specification (`docs/behavior-spec.md`).
- **[x] ISSUE-003**: Create Milestone Issue Map (`docs/issue-map.md`).
- **[x] ISSUE-004**: Clean up and label prototype UI: remove dead `/settings` link, remove dead `#` links, label placeholder stats, and fix `Ctrl+R` restart interception.

---

## Milestone M1 — Parity Foundation & Typing Engine (Complete)

- **[x] ISSUE-010**: **Container & Docker Compose Baseline**
  - *Acceptance*: Multi-stage Dockerfile for FastAPI/spaCy; `docker-compose.yml` orchestrating API and PostgreSQL services; reproducible local setup.
- **[x] ISSUE-011**: **Pure Typing State Reducer & Event Log**
  - *Acceptance*: Implement pure `typingReducer` with immutable input event logging in `packages/typing-engine` or frontend shared library; unit tests covering corrections, deletions, word jumps, and pauses.
- **[x] ISSUE-012**: **Unicode NFC & Grapheme Cluster Adaptation**
  - *Acceptance*: Tests verifying German umlauts (`ä, ö, ü, ß`), French diacritics (`é, è, ç`), Spanish (`ñ, ¿`), and IME composition events.
- **[x] ISSUE-013**: **Accurate WPM and Accuracy Metrics Calculation**
  - *Acceptance*: Standardized equations for Net WPM, Raw WPM, and accuracy implemented and verified against deterministic fixtures.
- **[x] ISSUE-014**: **Typing UI Integration & Post-Session Results View**
  - *Acceptance*: Replace legacy typing component with new reducer; render detailed post-session results dialog (WPM, accuracy, mistake breakdown).
- **[x] ISSUE-015**: **Playwright End-to-End Intake & Practice Flow**
  - *Acceptance*: Automated browser test verifying text upload, navigation to practice page, typing through a sentence, and asserting completion state.

---

## Milestone M2 — Owned Data & Durable Processing

- **[x] ISSUE-020**: **Schema Ownership Scoping & Alembic Migration Foundation**
  - *Acceptance*: Add non-nullable `owner_id` to `Text`, `Sentence`, `BackgroundJob`; replace `SQLModel.metadata.create_all` with versioned Alembic migrations.
- **[x] ISSUE-021**: **Transactional PostgreSQL Job Queue**
  - *Acceptance*: `background_jobs` table with `FOR UPDATE SKIP LOCKED` claiming, lease expiration heartbeats, and exponential retry backoff.
- **[x] ISSUE-022**: **Decoupled Application Factory & Optional Providers**
  - *Acceptance*: App boots and serves library/practice without requiring `DEEPSEEK_API_KEY` or external network access.
- **[x] ISSUE-023**: **Worker Process & spaCy Isolation**
  - *Acceptance*: Dedicated worker daemon consuming background jobs; moves heavy tokenization and sentence splitting off the web API thread.

---

## Milestone M3 — Budgeted Groq-First Enrichment

- **[x] ISSUE-030**: **Groq Provider Integration & Failover Circuit Breaker**
  - *Acceptance*: Low-latency Groq client with backpressure; graceful failover to DeepSeek on HTTP 429 or 5xx.
- **[x] ISSUE-031**: **Token Budgeting, Spend Caps, and Caching**
  - *Acceptance*: Daily token spend limits; database translation caching by `(lang, sentence_hash, prompt_version)`.
- **[x] ISSUE-032**: **Truthful Job Progress & Error Feedback UI**
  - *Acceptance*: Frontend clearly displays queue status, step-by-step progress, and honest error states if enrichment fails.

---

## Milestone M4 — Authentication & Learning History

- **[x] ISSUE-040**: **Managed Authentication Integration**
  - *Acceptance*: JWT/session validation on API routes; links authenticated user IDs to `owner_id`.
- **[x] ISSUE-041**: **Durable Learning Analytics & History**
  - *Acceptance*: Store completed practice sessions; compute historical accuracy trends, speed progression, and persistent weak words.
- **[x] ISSUE-042**: **User Data Export & Right to Erasure (GDPR/CCPA)**
  - *Acceptance*: `GET /api/user/export` returns complete JSON archive; `DELETE /api/user/account` purges all owned records via database cascades.

---

## Milestone M5 — Observability & Staging

- **[x] ISSUE-050**: **Structured Logging & Telemetry with Content Redaction**
  - *Acceptance*: Standardized JSON stdout logger; correlation IDs; automated redaction preventing user learning text from entering logs.
- **[x] ISSUE-051**: **CI/CD Pipeline & Staging Environment Deployment**
  - *Acceptance*: GitHub Actions running parallel lint, unit, migration, and Playwright tests; immutable image build and staging deploy.

---

## Milestone M6 — Private Beta & Production Readiness

- **[x] ISSUE-060**: **Accessibility (WCAG 2.1 AA) & Cross-Browser Audit**
  - *Acceptance*: Keyboard-only navigation; screen reader announcements; high-contrast checks via Axe.
- **[ ] ISSUE-061**: **Disaster Recovery & Backup Rehearsal**
  - *Acceptance*: Documented automated backup script and verified database recovery runbook.
