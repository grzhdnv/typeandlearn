# Queue dispatch update — 20 October 2026

API/worker dispatch unification is complete. Read
[queue acceptance](docs/queue-acceptance-2026-10-20.md) and ADR-0003.

- Upload/retry/regeneration enqueue only. API startup runs the same leased consumer
  as the CLI; set `EMBEDDED_WORKER_ENABLED=false` when using dedicated workers.
  Docker Compose disables the embedded API consumer.
- SQLite claims serialize before selection; PostgreSQL uses row/advisory locks.
  Only the current unexpired unique lease owner can finish/fail its job.
- Atomic retry/regeneration reuse pending jobs and reject leased work. Crash retries
  are bounded; final expired attempts become dead letters and failed texts.
- Recovery is at least once: external requests can be repeated after a crash.
  Cooperative lease checks prevent observed stale responses from overwriting a
  replacement's work; PostgreSQL concurrency still requires live acceptance.
- Verification: 112 backend tests, 31 frontend tests, 27 Chromium tests; full
  lint/types/build checks. A real isolated API plus two standalone worker processes
  verified one claim, truthful offline failure, original preservation and clean exit.
- Raw text/translation/word-list progress prints in enrichment were removed in favor
  of content-free structured logging. Existing SQLite ResourceWarnings remain.
- Local provider activation and caps below remain in effect. Preserve credentials
  and unrelated `opencode.json`.

Next: move intake preprocessing and optional metadata/filtering off the HTTP fast
path, then verify PostgreSQL/staging recovery. Jev remains deferred.

---

# Current handoff — 20 October 2026

Hint normalization, validation, and the expanded MiniMax technical acceptance are
complete. Read [the acceptance report](docs/minimax-acceptance-2026-10-20.md), then
[the provider comparison](docs/openrouter-evaluation-2026-10-20.md). Preserve the
unrelated `opencode.json` and user credentials.

- Five real synthetic storage/enrichment flows passed in German, French, Italian,
  Spanish, and English: 10 saved translations, 25 saved drills, fresh readback.
- Final acceptance: 25 MiniMax requests, 36,571 tokens, $0, no repair attempts.
  The actual frontend matcher found zero unavailable hints at 353 word positions.
- New backend coverage checks require all source occurrences and nonempty hints.
  One repair is allowed/accounted; exhausted output validation may select the next
  configured provider. Bad credentials, permanent errors and budgets still stop.
- UI hint lookup is Unicode- and occurrence-aware. Curly apostrophes, inverted
  punctuation, NFC, repeated meanings and separable-verb highlights are verified.
- Drill output cap: 4,096; other tasks: 2,048. Cache version: `v3-validated-hints`.
- MiniMax uses prompted JSON + low mandatory reasoning; its tool path is unreliable.
  Ultra is an alternative; Super's free endpoint returned 404 twice.
- User approved local Groq→MiniMax→DeepSeek activation on 20 October after the
  content-use disclosure. The ignored `.env` now enables it; repository defaults
  remain Groq/DeepSeek. Local OpenRouter limits are 16 RPM / 800 RPD, below the
  verified 1,000-RPD account tier. DeepSeek remains capped at $0.50/day and $5/month.
  MiniMax terms allow service-improvement use of inputs/outputs; no blanket
  no-training/ZDR was established. Keep this scope explicit for private material.
- Jev is explicitly deferred. CEFR grading and naturalness remain provisional.
- Offline verification: 102 backend / 31 frontend tests, lint/types/build, and
  27 Chromium tests. Existing SQLite ResourceWarnings remain.

The queue dispatch task below has since been completed; see the update above.
Staging/recovery and PostgreSQL acceptance remain open.
Use isolated learning databases and blank all provider keys in offline checks.
The live acceptance script uses temporary learning SQLite but the real shared quota
ledger; only synthetic content is authorized for such benchmarks. Run-only quota
and owner-token overrides are documented, not global app settings.

The original 19 October handoff below is historical background. Its OpenRouter
starting-state instructions are superseded by the completed report above.

---

# Session handoff — 19 October 2026

Resume on 20 October 2026. **First task: test OpenRouter free models.**
The user wants to continue in a new session; no automation or new chat was created.

## Start here

1. Read this file, `README.md`, and ADR-0005. Inspect Git status and the branch before
   editing. Preserve all local work; leave unrelated untracked `opencode.json` alone.
2. Current working branch: `codex/restore-local-flow`. Latest implementation commit:
   `7b6cda3` (`feat: govern Groq quotas and cap DeepSeek fallback spending`). The
   handoff documentation follows that commit. Work has been committed locally;
   do not assume this branch has been pushed or has an upstream.
3. Verify current OpenRouter model availability, free-model pricing/routing, quotas,
   structured-output support, and data-handling terms using official documentation
   and its model catalog. Do not guess model identifiers or reuse Groq quotas.
4. Check whether an OpenRouter key is configured without printing credentials.
   Ask the user only if a missing key or necessary preference blocks a live test.
5. Add a minimal, tested OpenRouter adapter and run the existing synthetic cases
   against a small shortlist of genuinely free models. Use explicit free model IDs,
   verify zero input/output prices, and disable paid model/provider fallback during
   the comparison. No paid OpenRouter use is authorized by this request.
6. Save comparative results, including failures, schema reliability, translations,
   hints, exercise quality, quota waits, and actual usage. Recommend whether an
   OpenRouter free model belongs in the routing order; preserve the working defaults
   until the evidence supports changing them.

## Working provider baseline

- Primary: Groq `openai/gpt-oss-120b`, low reasoning, native strict JSON schema.
- Fallback: DeepSeek `deepseek-flash`, thinking disabled, typed tool output.
- User-confirmed DeepSeek limits: **$0.50 per UTC day and $5 per UTC month**,
  configurable and shared across API/worker processes using the same database.
- Groq default application limits: 24 RPM / 800 RPD / 6,400 TPM / 160,000 TPD
  (20% below the supplied account screenshot). Headers/cooldowns may restrict more.
- Local Groq capacity waits up to ten seconds; upstream transient failures can select
  DeepSeek immediately. Bad requests/credentials do not trigger paid fallback.
- Every HTTP attempt reserves capacity before dispatch. Actual returned model/usage
  reconciles reservations; unknown billing retains the conservative reservation.
- No SDK retry stack; one bounded schema-repair attempt, separately accounted.
- All four tasks use the shared transport: metadata, filtering, translation, exercises.
- Prompts now follow the selected source language; cache version is `v2-multilingual`.

## OpenRouter integration traps

The current implementation intentionally supports only Groq and DeepSeek. Extending
just a model string or base URL is insufficient:

- `services/llm_service.py`: `_can_create_model`, `_create_model`, transport hostname
  allowlist, native-output selection, and task routing need an explicit new provider.
- `services/provider_governor.py`: quota/cost branching currently assumes the only
  non-Groq provider is DeepSeek. Add an explicit free OpenRouter policy; do not
  accidentally debit DeepSeek budgets or bypass reservations/accounting.
- `core/settings.py` and `.env.example`: add only necessary configuration; keep keys
  in the ignored local environment. Respect existing toolchain/dependency rules.
- `scripts/evaluate_providers.py`: model choices and defaults currently cover only
  Groq GPT-OSS, Groq Qwen, and DeepSeek. Extend its provider-specific comparison
  without silently enabling the application's paid fallback.
- Test real SDK request serialization using MockTransport, including free-only
  selection, returned-model accounting, 429/reset behavior, and permanent errors.
- Use synthetic content only. Do not submit personal library texts as benchmarks.

## Evidence and known limits

Read `docs/provider-evaluation-2026-10-19.md` and the frozen synthetic JSON under
`docs/evaluations/`. Each current model completed seven final tasks: translation in
German/French/Italian/Spanish/English, French metadata, and five Spanish exercises.
Qwen needed an explicit SDK native-schema profile/transformer; a separate probe hit
an additional 1,000 output-token/minute limit absent from the screenshot.

A real DeepSeek fallback flow also saved a synthetic French translation and five
exercises and reached the completed state. Learning storage was temporary;
dictionary lookup alone was mocked. All evaluation DeepSeek calls together were
estimated at $0.004437, already recorded in the application's shared quota ledger.

Remaining quality issues: CEFR difficulty estimates vary; DeepSeek sometimes places
multiple words in a single hint `words` entry. Complete hint/source coverage and
normalization are not yet enforced. The small comparison is not a quality ranking.

## Verification and running the app

Last verified: Ruff, Pyright, Python compilation, frontend type check/build,
**81 backend tests, 27 frontend tests, 21 Chromium browser tests**. Existing SQLite
unclosed-connection ResourceWarnings remain. PostgreSQL integration/concurrency,
production deployment, and private-beta acceptance have not been established.

Run `npm run dev` from the repository root (frontend 3000, backend 8000). Check port
availability first; do not assume yesterday's dev processes survived. Startup can
resume pending enrichment, so use isolated services/databases for experiments.

For full checks, keep tests off the personal database and disable live credentials:

```bash
check_dir=$(mktemp -d /private/tmp/typeandlearn-check.XXXXXX)
DATABASE_URL="sqlite:///$check_dir/check.sqlite" GROQ_API_KEY= DEEPSEEK_API_KEY= npm run check
npm run test:e2e -- --workers=1
```

Add an empty OpenRouter key override to offline checks once the adapter exists.
Browser tests already start isolated services on ports 13000/18000 with temporary
SQLite storage. Live provider evaluation is opt-in and uses the shared real quota
ledger; CI must not call live models.

## Preserve the user's practice decisions

- After sentence completion, pause for review; Enter advances. No immediate jump.
- Show the Enter instruction between the typing instruction and Ctrl+R restart help.
- `[` / `]` navigate sentences without adding typing mistakes.
- Detailed mistake review was explicitly removed at the user's request; do not restore.
- Resume incomplete original-text progress; completed (100%) texts restart at sentence one.

After the OpenRouter comparison, the main engineering backlog is still one API/worker
job-dispatch path (currently capable of duplicate execution), broader multilingual
browser/keyboard coverage, and staging/recovery verification. See `docs/roadmap.md`.
