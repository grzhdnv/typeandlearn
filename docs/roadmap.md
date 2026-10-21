# TypeAndLearn Roadmap

Updated: 21 October 2026

This is the current backlog. The production plan records the target architecture;
checkmarks in the historical issue map do not establish production readiness.

## Verified local baseline

- FastAPI/SolidJS app with SQLite persistence and Alembic migrations.
- Text intake with optional AI metadata and explicit language selection for offline use.
- Library browsing, metadata save/reload, deletion, and truthful enrichment failures.
- Original and generated typing practice, sentence-specific restart/reset, keyboard
  controls, saved original-text completion progress, results, and practice history.
- Provider routing, owner scoping, backend JWT validation, analytics, and export/delete
  implementations with automated backend coverage.
- Ruff, Python type checking, frontend type checking and build, 121 backend tests,
  32 frontend unit tests, and 29 isolated Chromium browser regressions.
- Live synthetic comparison across five languages, metadata, exercises, and a real
  DeepSeek fallback flow; shared quotas and approved $0.50/day and $5/month limits.

## Completed: OpenRouter free-model comparison

- [x] Verify current models/limits and implement an offline-tested free-only adapter.
- [x] Compare Ultra 550B, Dots 280B, and Super 120B on synthetic fixtures. Ultra and
  Dots passed 7/7 with reasoning off; Super returned upstream 404s. See
  `openrouter-evaluation-2026-10-20.md`. Groq/DeepSeek defaults remain unchanged.
- [x] Compare MiniMax M3.1 Flash via prompted JSON output: 7/7 with mandatory low
  reasoning, better hint lookup coverage than Ultra in this small sample.
- [x] Normalize/validate hint coverage and run the real MiniMax pipeline in all five
  languages; verify the three-provider fallback chain. See `minimax-acceptance-2026-10-20.md`.
- [x] Review MiniMax content-use terms and document opt-in routing. Global defaults
  remain unchanged; no blanket no-training/ZDR commitment was established.
- [ ] Improve CEFR grading and generated exercise naturalness with a labeled review set.

## Next: reliable processing and realistic practice

- [x] Unify API and standalone worker dispatch through durable leases. SQLite
  concurrency, expired-worker fencing, crash budgets, and queue resumption across
  owners are verified; local PostgreSQL 18 acceptance is now verified. See
  `queue-acceptance-2026-10-20.md` and `postgresql-acceptance-2026-10-21.md`.
- [x] Move intake preprocessing, metadata, and vocabulary filtering off the HTTP
  fast path. Source/job persistence precedes all NLP/provider work; preparation
  checkpoints, user edits/progress, missing-model recovery and browser polling are
  verified. See `intake-acceptance-2026-10-20.md`.
- [x] Verify local Groq/DeepSeek retry classification, quota reservations, actual-model
  usage accounting, and daily/monthly spend caps; PostgreSQL reservation concurrency
  is also verified.
- [ ] Exercise longer multilingual texts, mobile keyboards, real IME/dead keys,
  screen readers, and more browsers; broaden accessibility checks beyond the
  tested results-dialog focus containment.
- [ ] Repair and validate shared contract artifacts against the runtime API.
- [x] Normalize absent author/category metadata, hide legacy null badges and persist
  explicit clearing without allowing inference to overwrite user edits.
- [ ] Replace remaining placeholder product copy and clarify empty legacy records.
- [x] Verify local PostgreSQL 18.6 migrations, startup serialization, queue concurrency,
  expiry/heartbeat/crash recovery and isolated Compose volume persistence; 10 live
  tests plus a synthetic PostgreSQL 16-to-18 dump/restore rehearsal. See
  `postgresql-acceptance-2026-10-21.md`.

## Before private beta

- [ ] Complete browser authentication/session integration and security review.
- [ ] Deploy a real protected staging service; current workflow builds/smoke-tests only.
- [ ] Reproduce PostgreSQL migration/recovery and operational backup/restore on
  protected staging, including previous-application-version compatibility.
- [ ] Rehearse provider outages, load, recovery, and observability on staging.
- [ ] Complete legal/privacy/contact surfaces and sample-text licensing review.

## Historical reference

The production plan and issue map preserve the original M0–M6 sequence.
The `legacy/v1` branch and `v1-final` tag preserve collaborative v1.
