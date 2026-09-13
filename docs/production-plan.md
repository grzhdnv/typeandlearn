# TypeAndLearn Production Plan

Updated: 30 August 2026

## Outcome and scope

Ship a reliable language-learning typing app in which a user can add a text,
practice it through deterministic mechanics, receive optional LLM-enhanced
translations and exercises asynchronously, and retain accurate private learning
history.

Production v1 excludes leaderboards, competitive anti-cheat, social features, a
large theme catalog, and broad game modifiers. Those are Monkeytype strengths, but
they do not prove TypeAndLearn's core learning loop.

## Current assessment

The repository is a viable prototype, not a production candidate yet.

Strengths:

- FastAPI/SolidJS boundaries are clear enough to evolve.
- SQLite/PostgreSQL persistence is behind a repository layer.
- Local spaCy preprocessing covers German, French, Italian, Spanish, and English.
- Text CRUD, progress, translations, generated exercises, and dictionary lookup
  exist.
- The current quality gate passes Pyright, 9 backend tests, Python compilation,
  frontend type checking, and the Vite production build.

Production blockers:

- LLM construction happens at application import, coupling basic library access to
  provider credentials.
- FastAPI background tasks and ad hoc threads are not a durable work queue.
- Failed enrichment steps can still end with the text marked `processed`.
- Retries are duplicated and classified by exception-string matching.
- Groq is not currently first; DeepSeek is the default and no fallback is configured.
- Logging mixes `print`, console calls, and one local file without correlation,
  metrics, traces, or a complete redaction policy.
- Intake is multiple independent transactions, schema evolution uses `create_all`,
  and library hydration produces N+1 queries.
- Progress stores ambiguous indices and cannot represent attempts, timing, errors,
  modes, or history.
- Typing completes on input length even with mistakes and lacks a pure engine,
  WPM/accuracy, IME/composition, Unicode graphemes, paste policy, and restart logic.
- WPM/accuracy are placeholders; Settings, history, account, and legal controls are
  dead; dictionary tooltips are too large for the practice surface.
- There are no frontend/component/E2E/accessibility/load/migration/failure tests.
- CI only checks source and build. There is no delivery, rollback, security scan,
  environment protection, backup, or recovery path.
- Authentication, ownership, data export/deletion, and production operations are
  absent.

## What to take from Monkeytype

The comparison used Monkeytype commit
`91bd24bb8513785c7364cbea29296ff7adafac41` from 15 August 2026.

Adopt as independently implemented behavior:

1. A versioned input event log from which session state and statistics are derived.
2. Pure statistics functions. Use the standard
   `WPM = correct characters / 5 / elapsed minutes`; define raw WPM and accuracy
   separately and publish examples.
3. Separate browser input adaptation, session state, statistics, caret, and rendering.
4. Deterministic fixtures for corrections, extra/missed characters, word boundaries,
   newlines, IME, dead keys, deletion variants, and timing stalls.
5. One engine configured for original sentence/paragraph, frequency or weak-word
   drills, and generated exercises.
6. A quiet focus mode plus optional live statistics and useful post-session analytics.
7. Caret quality, focus recovery, reduced motion, keyboard control, and accessible
   interaction.
8. Focused tests, shared contracts, asset validation, dependency automation,
   path-aware CI, durable jobs, and operational metrics.

Do not adopt for v1: leaderboards, achievements, anti-cheat, many themes/settings,
or Monkeytype's legacy migration structure. Monkeytype is GPL-3.0. Do not copy its
source into TypeAndLearn without a deliberate licensing decision; maintain an
original behavior specification and implementation.

## Target architecture

- Static SolidJS frontend on a CDN/static host.
- FastAPI API container built through an application factory.
- PostgreSQL as production source of truth; SQLite only for local/small tests.
- Separate worker for deterministic preprocessing and LLM enrichment.
- Durable PostgreSQL work items initially, behind a queue interface. Claim with
  `FOR UPDATE SKIP LOCKED`, renew leases by heartbeat, reclaim expired work, make
  handlers idempotent, and prune terminal attempts by retention policy. Introduce
  Redis only when measured load justifies another service.
- Alembic migrations, foreign keys, uniqueness/check constraints, UTC timestamps,
  transactional intake, and indexes derived from query paths.
- Container/Compose topology early so local development and CI resemble production.

Every owned row gets `owner_id` in the first production schema. Full login UI may
arrive later, but ownership must not be retrofitted after text, job, and practice
contracts stabilize.

## Deterministic core

Keep these paths deterministic:

- input validation, size limits, sanitization, and normalization;
- language allowlisting, sentence/paragraph segmentation, lemmatization, frequency
  extraction, and vocabulary selection;
- title fallback and explicit `Unrated` difficulty;
- typing state, progress, metrics, history, and weak-spot scoring;
- routing budgets, retry classes, cache keys, job transitions, and output validators.

The HTTP intake fast path validates encoding/size, performs basic normalization,
persists the raw text, and returns `202`. spaCy runs in the worker so CPU and model
memory do not block API workers. The text becomes practiceable when deterministic
processing finishes. No LLM or dictionary credential is required for intake,
library access, or original/frequency practice.

User metadata is authoritative. Missing title uses a deterministic first line,
filename, or `Untitled`; missing difficulty is `Unrated`. LLM metadata suggestions
are optional.

Production v1 must either import a pinned, license-reviewed multilingual dictionary
dataset into a local cache or omit definitions. Do not call best-effort Wiktionary
HTTP endpoints in the live practice path.

## Predictable LLM workflows

Use typed tasks, not a general-purpose agent:

- `translate_sentence_v1`
- `generate_hint_groups_v1`
- `generate_practice_set_v1`
- optional `suggest_metadata_v1`

Each sentence remains a logical task. The scheduler may batch 5–20 compatible items
into one provider request with stable item ids; validation, status, and retry remain
per item.

Persist task/schema/prompt versions, normalized input hash, idempotency key,
language, record ids, provider policy, model, token/time/retry budgets, status, and
attempts. Attempt records contain provider, typed error, latency, token usage,
fallback reason, and timestamps. Terminal states are `succeeded`, `degraded`,
`failed`, or `cancelled`; partial failure is never reported as success.

Provider policy:

- Groq is first for capability-tested structured tasks. As of this plan, a current
  candidate is `qwen/qwen3.8-27b`; the model id remains configuration, not domain
  code.
- A Groq 429 pauses work until the advertised reset time. It does not immediately
  spill a burst into the paid fallback.
- DeepSeek `deepseek-v4-flash` handles sustained Groq outage, explicit deadline or
  capacity shortfall, or bounded structured-output repair, only under per-user and
  global daily/monthly spend caps.
- Do not fall back on bad credentials, invalid requests, policy rejection, or
  deterministic input validation errors.
- Centralize retries. Honor `Retry-After` and provider headers, add jitter, limit
  concurrency, cap attempts, and use a circuit breaker.
- Cache by task type, normalized input, language, prompt version, schema version,
  and model policy.

Quality gates include Pydantic validation, target-language checks, exact item counts,
hint/source coverage, length limits, and safe-text rules. Prompt/model changes run
frozen fixtures for all supported languages plus a small human-scored sample before
canary rollout. Pull-request CI never calls live models.

Raw source, prompts, and outputs stay out of normal logs. If malformed output cannot
otherwise be diagnosed, an optional encrypted failure quarantine may retain only
failed payloads for at most seven days with authorization and audit logging; it is
disabled by default.

## Typing and learning model

Implement a pure, versioned session reducer fed by `beforeinput`, `input`,
`compositionstart/update/end`, key, and timer adapters. Normalize target/input to NFC
and segment grapheme clusters with `Intl.Segmenter` or a tested fallback. Define
paste, correction, completion, and shortcut rules explicitly.

Persist `practice_sessions`, compact optional event traces, and per-item outcomes.
Session summaries include WPM, raw WPM, accuracy, duration, error characters/words,
hint usage, and weak vocabulary. Avoid row-per-keystroke storage unless evidence
shows it is required.

## Observability and privacy

- One structured JSON logger to stdout.
- Propagate `request_id`, opaque `user_id`, `text_id`, `job_id`, and `attempt_id`;
  return request ids in errors.
- Redact authorization, cookies, API keys, and all raw learning/provider content.
  Log lengths, hashes, typed outcomes, and aggregate usage instead.
- OpenTelemetry across HTTP, database, queue, and providers.
- Backend/frontend error capture with release/environment tags and no practice text.
- Metrics for HTTP, DB pool, queue depth/age, job states/duration, provider failures,
  429s, fallback, token use, validation, cache hits, and practice completion.
- Liveness/readiness and worker health endpoints.
- Alerts and runbooks for SLO burn, stuck jobs, old work, fallback spikes, and backup
  failures.

Private-beta objectives:

- API availability at least 99.5% monthly.
- p95 non-enrichment API latency below 500 ms.
- keystroke-to-render feedback below 50 ms on a normal laptop.
- at least 99% of accepted enrichment jobs reach a truthful terminal state.
- restore point within 24 hours and restore within 4 hours, proven by rehearsal.

## Test strategy

1. Unit/property tests for typing, graphemes, WPM/accuracy, preprocessing, routing,
   spend limits, retry classification, cache keys, and job transitions.
2. Solid component tests for library, intake, job/error states, typing, hints, results,
   keyboard interaction, and recovery.
3. PostgreSQL integration tests for transactions, migrations, constraints, leasing,
   idempotency, and ownership.
4. Provider contract tests on a budgeted schedule, never in ordinary PR CI.
5. Playwright flows for intake-to-practice, enrichment success/fallback/failure,
   completion/history, deletion/export, mobile viewport, and keyboard-only use.
6. axe plus manual keyboard/screen-reader verification of the practice loop.
7. Load/soak tests for reads, sessions, leases, and Groq quota exhaustion without
   duplicate work or paid-fallback storms.
8. Backup/restore and migration rollback rehearsals.
9. N/N-1 rolling compatibility: migrate a populated N-1 database to N, run the N-1
   API against schema N, then run version N.

Critical typing/statistics and job-state modules need branch and property coverage,
not only a global percentage. Start with an 80% changed-line threshold.

## CI/CD and Copilot review

Pull requests run cancellable least-privilege jobs for formatting/lint/contracts,
Python type/unit/integration/migration/coverage, frontend type/component/build,
Playwright with fake providers and PostgreSQL, dependency/secret/CodeQL/container
scans, and immutable artifact builds. Pin third-party Actions by commit SHA.

Merge to `main` promotes the built commit artifact to staging, applies forward-safe
migrations, and runs smoke tests. Production is a protected GitHub Environment with
manual approval during private beta. Promote the exact staged digest, support
readiness-gated rolling/blue-green deploys, and keep the previous digest available
for rollback.

Automatic Copilot review is a GitHub branch-ruleset setting, not a normal Actions
workflow. Add concise `.github/copilot-instructions.md` plus path-specific Python,
frontend, migration, LLM, and CI instructions. An administrator then enables
“Automatically request Copilot code review” and “Review new pushes” for `main`.
Use Balanced effort for cross-service/security-sensitive changes if available.
Deterministic checks and at least one human approval remain required; Copilot is
advisory.

## Milestones

### M0 — decisions and contracts (3–5 days)

Write ADRs for scope, ownership/auth, PostgreSQL/jobs, dictionary licensing, LLM
routing/spend, metric semantics, privacy, hosting, and Monkeytype clean-room policy.
Create the issue map and remove or label dead/misleading UI.

### M1 — parity foundation and typing engine (1–2 weeks)

Add containers/Compose, frontend test harness, pure typing/event/statistics modules,
NFC/grapheme/IME fixtures, restart/results, and the first Playwright flow.

### M2 — owned data and durable processing (1–2 weeks)

Add owner-scoped schema/repositories, Alembic/PostgreSQL CI, app factory and optional
providers, atomic intake, durable jobs/attempts, spaCy worker processing, leases,
idempotency, truthful states, and recovery tests.

### M3 — budgeted Groq-first enrichment (1–2 weeks)

Add batched provider transport, Groq backpressure, capped DeepSeek fallback, cache,
prompt registry, validators/evals, usage accounting, controls, and truthful progress
and retry UI.

### M4 — authentication and learning history (1–2 weeks)

Connect managed identity to the ownership foundation; add secure sessions, history,
weak spots, resume, delete/export, rate limits, headers, threat model, and horizontal
authorization tests.

### M5 — observability and staging (1 week)

Add telemetry, dashboards/alerts/runbooks, split deterministic CI/security gates,
immutable staging CD, N/N-1 checks, smoke/rollback, Copilot instruction files, and
the administrator settings checklist.

### M6 — private beta and production (1–2 weeks soak)

Run accessibility/browser/device/load/provider-outage/migration/backup game days,
add licensed sample texts and real legal/privacy/contact surfaces, fix SLO failures,
and promote the staged digest.

## First pull-request sequence

1. ADRs, launch checklist, issue map, behavior spec, and honest prototype UI.
2. Containers/Compose, format/lint/test/security baseline, and parallel CI.
3. Pure typing reducer/statistics with Unicode/IME fixtures and property tests.
4. Typing UI integration, restart/results, and Playwright complete-session flow.
5. Owner foundation, Alembic/PostgreSQL constraints, repositories, N/N-1 harness.
6. App factory, optional providers, health, and transactional intake fast path.
7. Durable worker, leases/heartbeat/recovery, spaCy offload, idempotency tests.
8. Batched Groq-first routing, backpressure, spend caps, DeepSeek fallback, evals.
9. Auth/session, practice history/weak spots, and data export/deletion.
10. Telemetry, staging delivery/rollback, and GitHub review governance as separate
    reviewable PRs if any contains more than one independently testable behavior.

## Adversarial review disposition

Antigravity reviewed a sanitized draft while the private repository was explicitly
sealed from its reads.

Accepted or adapted: early ownership, spaCy worker processing, provider batching
with per-item granularity, Groq backpressure and spend-capped fallback, explicit
PostgreSQL leases, early containers, Unicode/IME and N/N-1 tests, smaller final PRs,
and an explicit dictionary decision.

Not accepted literally:

- Antigravity called the Groq and DeepSeek model ids speculative. Current official
  provider documentation lists them on this date; they remain configurable because
  catalogs change.
- It claimed that reading GPL source automatically “taints” another codebase. The
  plan instead prohibits copying protected implementation and requires original
  behavior-driven code. Seek legal advice before any future code reuse.
- Weekly queue-table partitioning and encrypted failure storage are not defaults;
  add them only when measured volume or an explicit debugging need justifies their
  cost and privacy risk.
