# Resume update — PostgreSQL 18 acceptance, 21 October 2026

This update supersedes older statements that PostgreSQL/Docker are unavailable.
Read `docs/postgresql-acceptance-2026-10-21.md` first for current database acceptance.

- Shared `postgresql` and `containers` capabilities pass doctor. Docker/Colima works;
  native PostgreSQL is 18.6. Invoke registered tools through the hub's `bin/` wrappers
  and select Docker context `colima-hub` explicitly.
- User requested upgrading TypeAndLearn to PostgreSQL 18 and confirmed there is no
  valuable database data yet; schema redesign remains possible if justified.
  Compose now pins PostgreSQL 18.6 by image digest and uses a new `postgres18_data`
  volume at `/var/lib/postgresql`. Native dev still defaults to SQLite.
- Live acceptance found Alembic's 32-character version column rejecting existing
  long revision IDs. The migration environment now widens it to 128 and holds a
  PostgreSQL transaction advisory lock throughout startup migrations. No learning
  table redesign or revision-ID rewrite was needed.
- 10 live PostgreSQL tests pass: populated migrations/guarded rollback/adoption,
  concurrent startup/claimers/duplicate jobs/requeue, heartbeat/lease expiry and
  budgets, owner-scoped startup recovery, real API plus two CLI workers, process
  crash after preparation preserving sentence IDs/progress, provider reservations.
- Compose persistence across stop/start and a synthetic 16-to-18 dump/restore with
  sentence/progress readback passed separately. Disposable acceptance resources
  were cleaned up; no personal database or existing volume was rewritten.
- Required checks: 121 backend / 32 frontend / 29 Chromium tests, Ruff, Pyright,
  compilation, frontend types/build. Existing SQLite ResourceWarnings remain.
- Dedicated PostgreSQL 18 CI job added; remote CI not run. PostgreSQL acceptance
  and the earlier metadata repair are committed locally on the current branch.
  No push was requested; leave `opencode.json` alone.
- Next: CEFR/exercise-quality rubric and labeled synthetic review set, realistic
  practice/accessibility, then protected staging/security/operational recovery.
  Local PostgreSQL acceptance does not establish hosted staging or exactly-once
  processing. See the current roadmap for remaining gates.

---

# Resume update — metadata badge repair, 20 October 2026

Read this update before the older resume section below. The reported category bug
is fixed in the working tree: read-only inspection confirmed the matching legacy
record contained the literal string `"null"`; the running development API now returns
JSON null for it without modifying personal records.

- Shared author/category normalization handles empty strings and case-insensitive
  `null`, `none`, `undefined` at schema, intake and metadata persistence boundaries.
  API readback cleans existing records; frontend list reads also tolerate older APIs.
- Empty/explicit-null edits clear these two fields; omitted fields remain untouched.
  User-cleared fields are excluded from later inference. Valid labels containing
  words such as `Null hypothesis` are preserved. Invalid types return validation errors.
- Full `npm run check`: 121 backend / 32 frontend tests, Ruff, Pyright, compilation,
  frontend types/build passed. Chromium suite: 29 passed, including legacy badge,
  editing/reload and clearing coverage. Checks used isolated databases and blank keys.
  Existing SQLite ResourceWarnings remain a separate finding.
- Git fetch succeeded; branch remains `codex/restore-local-flow` with no upstream.
  This session's code/docs are uncommitted; unrelated `opencode.json` is untouched.
- Local API health is 200. Existing dev services were reused; no duplicate started.
- PostgreSQL/Docker remain unavailable on this host. The staging workflow only
  smoke-tests SQLite containers and no hosted staging endpoint is recorded.
  Live PostgreSQL migrations/concurrency/recovery remain unverified; no tools were
  installed and no service was deployed. Continue the acceptance/quality backlog below.

---

# Resume here — session handoff, 20 October 2026

The user is stopping for now and will continue in a new session. No automation,
new chat, deployment, or push was requested. Completed implementation is committed
locally; the remaining work is acceptance and quality, not finishing today's code.

## Checkout and first reads

- Project: `/Users/mgrzhdnv/Documents/dev/typeandlearn` (independent Git repository).
  Shared hub: `/Users/mgrzhdnv/ai`; its dashboard already matches the README.
- Branch: `codex/restore-local-flow`. Latest implementation: `3b52632`
  (`feat: prepare uploaded texts asynchronously through durable jobs`). Queue fix:
  `30aaed7`; hints/provider acceptance: `e3e2bcd`; activation documentation: `d6a15e9`.
  This handoff is a subsequent documentation commit. Do not assume an upstream or
  that this branch has been pushed. Inspect status/remotes and fetch before coding;
  preserve local work and use fast-forward-only synchronization where applicable.
- The only project untracked file at handoff is unrelated `opencode.json`: leave it
  alone. Never print or commit `.env`, provider keys, personal learning data, or logs
  containing content. Outer-hub untracked outputs are also unrelated.
- Read `README.md`, `.github/copilot-instructions.md`,
  `docs/intake-acceptance-2026-10-20.md`, `docs/queue-acceptance-2026-10-20.md`,
  ADR-0003 and ADR-0005, then `docs/roadmap.md`.
- Use the existing locked dependencies and stable toolchain. Do not install Docker,
  PostgreSQL, packages, or substitute tools merely because a capability is absent.

## Current behavior to preserve

- Upload commits source/options/job before any NLP or provider call. The same
  durable consumer performs preparation, metadata, filtering, translations and drills.
- Local API starts one embedded worker by default. Dedicated-worker deployments use
  `EMBEDDED_WORKER_ENABLED=false`; Docker Compose already selects that arrangement.
- Explicit language lets local sentence preparation finish before optional metadata
  waits, enabling original practice early. Automatic language detection happens in
  the worker; offline upload still requires an explicit supported language.
- Source preview/preparation state covers the period before sentences exist. Missing
  models/detection failures retain source and actionable errors. Retries preserve
  sentence IDs, boundaries, progress, and explicit user metadata edits.
- Lease claims are serialized on SQLite; PostgreSQL uses row/advisory locks. Unique
  per-attempt tokens protect job completion/failure, heartbeat renews active work,
  and final crashed attempts dead-letter. Recovery is **at least once**; lease checks
  around persistence are cooperative, not transactional fencing of every write or
  an exactly-once guarantee for external provider requests.
- Migration head is `0006_durable_intake`, applied to the local development database.
  Its downgrade retains nullable source/options columns and refuses to strand
  source-only uploads. Do not force rollback or delete sources to bypass this guard.
- Preserve typing behavior: pause after completion, Enter advances, brackets navigate,
  incomplete sessions resume, completed sessions restart; no detailed mistake review.

## Approved providers and scope

- User explicitly approved local **Groq GPT-OSS 120B → OpenRouter MiniMax M3.1 Flash
  `:free` → DeepSeek Flash**, after disclosure that MiniMax may use inputs/outputs
  for service improvement. That approval persists; do not ask again just to resume.
- Local free OpenRouter limits: 16 RPM / 800 RPD, below the verified 1,000-RPD tier.
  DeepSeek ceilings remain **$0.50 per UTC day / $5 per UTC month**. Repository
  defaults remain Groq/DeepSeek; local `.env` activates the extra free step.
- Cache/prompt version: `v3-validated-hints`; output limits 2,048 generally / 4,096
  for drills. Free MiniMax uses prompted JSON and mandatory low reasoning.
- Live benchmarks use synthetic content only and the real shared provider ledger;
  never reset accounting or submit personal library content as a benchmark. The
  five-language MiniMax acceptance report is already complete; no repeat is needed.
- Jev is explicitly deferred. CEFR labels and exercise naturalness are provisional.

## Verification and local runtime

- Latest full `npm run check`: **118 backend / 32 frontend tests**, Ruff, Pyright,
  compilation, frontend types/build all passed. Latest Chromium suite: **28 passed**.
- Real isolated Uvicorn API plus two CLI workers passed: one claim, background NLP,
  truthful offline enrichment failure, original preservation, clean SIGTERM exits.
- Existing SQLite unclosed-connection ResourceWarnings remain a separate finding.
- Development API/frontend were healthy on ports 8000/3000 at the end of implementation.
  Check the ports and health again in a new session; do not start duplicate servers
  or assume old process/session IDs remain valid. Start with `npm run dev` if needed.
- Offline check example (from the project root):

```bash
qa_dir=$(mktemp -d /private/tmp/typeandlearn-check.XXXXXX)
DATABASE_URL="sqlite:///$qa_dir/check.sqlite" GROQ_API_KEY= DEEPSEEK_API_KEY= OPENROUTER_API_KEY= EMBEDDED_WORKER_ENABLED=false npm run check
npm run test:e2e
```

Browser configuration supplies temporary services/databases and blank keys itself.
Never run general checks against the personal development database or active keys.

## UI bug reported after handoff — resolved by update above

The user supplied a screenshot of the first German/A1 library practice card,
"Hallo Welt. Das ist ein Test.", showing a gray `null` badge below its title.
The badge at `apps/frontend/src/features/library/pages/LibraryPage.tsx` is the
category (`<Show when={text.category}>`). An actual null value would be hidden;
the screenshot therefore suggests the stored/API category is the literal string
`"null"`. The underlying record has not been inspected, so confirm before fixing.

Normalize absent metadata consistently at the API/storage boundary and hide
placeholder category values in card rendering as appropriate. Check author and
other optional metadata for the same issue. Verify new inference and existing
records, preserving valid labels and user edits; add a focused browser regression.
No fix or personal-record cleanup has been applied. The user explicitly requested
adding this bug to the handoff for the next session.

## Next work, in order

1. Verify live PostgreSQL migrations, queue concurrency, and recovery using an
   isolated database and existing approved runtime. PostgreSQL/Docker was not
   available for live acceptance in this session; SQLite results do not establish it.
   Inspect staging/container configuration and available tools first. Cover populated
   upgrade, source-preserving rollback, API/worker concurrent startup migrations,
   multiple claimers including duplicate jobs for one text, heartbeat/expired leases,
   retry budgets, another owner's queued raw source, and crash/restart checkpoints.
   Keep real provider keys disabled and replace external calls with synthetic fixtures.
   Do not deploy a hosted service or change the toolchain silently.
2. Improve CEFR grading and generated exercise naturalness using labeled synthetic
   examples and an explicit acceptance rubric. Mechanical hints/schema checks already
   pass; they do not prove pedagogical quality. See the MiniMax acceptance report.
3. Continue realistic multilingual/mobile/IME/accessibility coverage and private-beta
   staging/security/recovery work from the roadmap. Update README/dashboard together
   if status or next actions change.

The sections below preserve completed milestones and older context. Their test
counts and future-task descriptions are historical; this resume section takes priority.

---

# Background intake update — 20 October 2026

Source-first asynchronous intake is complete. Read
[intake acceptance](docs/intake-acceptance-2026-10-20.md).

- HTTP upload only validates inexpensive choices and atomically saves the source,
  preparation options, and queue job. No spaCy load, NLP pass, metadata call, or AI
  filtering runs on upload/regeneration requests.
- Worker checkpoints local sentence preparation, metadata, and vocabulary work.
  Explicit language enables original practice before optional AI metadata finishes.
  Without a language, the worker detects it first; offline intake still asks for an
  explicit supported language before saving.
- Until sentence preparation finishes, the practice page shows a preparation state
  and expandable saved-source preview. Polling exposes the prepared typing canvas;
  empty sentence controls are hidden. Errors preserve the source for correction/retry.
- Sentence IDs/boundaries are not replaced on enrichment retry or regeneration.
  Metadata inference cannot overwrite user edits, and worker/progress writes update
  only their own fields. Explicit AI-filter regeneration failures retain old results.
- Migration `0006_durable_intake` adds nullable source/options columns. Older rows
  remain valid. Compatibility downgrade retains source columns and refuses to strand
  unprepared uploads; migration fixtures verify upgrade, adoption and rollback.
- Verification: full lint/types/build/compile checks, 118 backend / 32 frontend /
  28 Chromium tests. Real isolated API + two CLI workers also passed with synthetic
  content and disabled keys. Existing SQLite ResourceWarnings remain separate.
- Provider chain/caps below remain approved and unchanged. No new live inference
  benchmark or dependency installation was required. Preserve unrelated `opencode.json`.

Next: live PostgreSQL migration/lease recovery acceptance on staging, improve
CEFR/exercise naturalness with labeled examples, then broader practice/accessibility.
Jev remains deferred.

---

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

That intake task is now complete; see the newer update above. PostgreSQL/staging
recovery remains open. Jev remains deferred.

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
