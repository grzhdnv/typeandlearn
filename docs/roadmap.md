# TypeAndLearn Roadmap

Updated: 19 October 2026

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
- Ruff, Python type checking, frontend type checking and build, 81 backend tests,
  27 frontend unit tests, and 21 isolated Chromium browser regressions.
- Live synthetic comparison across five languages, metadata, exercises, and a real
  DeepSeek fallback flow; shared quotas and approved $0.50/day and $5/month limits.

## Immediate next session: OpenRouter free models

- [ ] Follow `../HANDOFF.md`: verify current free models and account limits, add an
  explicit adapter, and compare a small shortlist on the synthetic fixtures with
  paid OpenRouter routing disabled. Preserve working defaults until evaluated.

## Next: reliable processing and realistic practice

- [ ] Make API and standalone worker use one job dispatch/claim path; avoid duplicate
  execution, and verify failures/recovery across restarts and owners.
- [ ] Move intake preprocessing and optional AI metadata off the HTTP fast path.
- [x] Verify local Groq/DeepSeek retry classification, quota reservations, actual-model
  usage accounting, and daily/monthly spend caps; PostgreSQL acceptance remains below.
- [ ] Exercise longer multilingual texts, mobile keyboards, real IME/dead keys,
  screen readers, and more browsers; broaden accessibility checks beyond the
  tested results-dialog focus containment.
- [ ] Repair and validate shared contract artifacts against the runtime API.
- [ ] Replace remaining placeholder product copy and clarify empty legacy records.

## Before private beta

- [ ] Complete browser authentication/session integration and security review.
- [ ] Deploy a real protected staging service; current workflow builds/smoke-tests only.
- [ ] Verify PostgreSQL migrations, lease concurrency, rollback, and backup/restore
  against a populated database, including the previous application version.
- [ ] Rehearse provider outages, load, recovery, and observability on staging.
- [ ] Complete legal/privacy/contact surfaces and sample-text licensing review.

## Historical reference

The production plan and issue map preserve the original M0–M6 sequence.
The `legacy/v1` branch and `v1-final` tag preserve collaborative v1.
