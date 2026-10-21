# Background intake acceptance — 20 October 2026

Uploads now return after inexpensive validation and one atomic source/job write.
All spaCy work, metadata inference, and AI vocabulary filtering run in the durable
consumer. Regeneration also enqueues its requested filter without doing NLP or
provider work in the HTTP handler.

## Preparation and recovery

`texts.source_text` preserves the uploaded source. Nullable `intake_options` stores
the selected filter, omitted metadata fields, and preparation/vocabulary checkpoints.
The job payload contains routing options rather than another copy of the text.
Existing library rows with neither new field continue through the old sentence data.

With an explicit supported language, the worker prepares and saves sentences before
waiting for optional metadata. The original typing flow then works while AI work
continues. With automatic language selection, inference precedes local preparation.
Without provider credentials, the upload form still asks for an explicit language.
Transient detection failures preserve the source and permit detection on retry.
Missing models fail asynchronously with the setup command and saved source intact.

The practice page polls while queued/preparing, shows an accessible preparation
message and expandable plain-text source preview, and hides empty sentence controls.
It offers typing when stable sentence rows arrive. Failed preparation preserves the
source preview rather than implying that unavailable sentence practice is ready.

Initial sentence rows and counts are committed together. Once prepared, retries and
vocabulary regeneration retain sentence IDs, boundaries and progress. Inferred
metadata fills only omitted values still at their defaults; explicit edits remove
those fields from inference eligibility. Progress, metadata, and worker status
writes touch their own fields. Explicit AI-filter regeneration failures remain
visible and preserve previous vocabulary and drills; intake retains its existing
spaCy fallback when optional AI filtering is unavailable.

## Schema compatibility

Migration `0006_durable_intake` adds two nullable columns without reprocessing old
texts. It adopts an already-created test schema and can be upgraded repeatedly.
Its compatibility downgrade retains the additive columns, preserving sources and
checkpoints. It refuses downgrade if a source-only upload has not been prepared;
prepare the upload or explicitly delete it before returning to an older consumer
that cannot understand the preparation plan. No uploaded content is silently dropped.
Rollback/re-upgrade fixtures preserve existing library rows and uploaded sources.
Live PostgreSQL migration and recovery acceptance remains open.

## Verification

`npm run check` passed: Ruff, Pyright, compilation, **118 backend tests**, frontend
build/type checks and **32 frontend unit tests**. **28 isolated Chromium tests**
passed. All automated checks use temporary databases and disabled provider keys;
API fixtures replace only external LLM/dictionary responses while exercising real
spaCy, HTTP routes, repositories, durable claims, and SQLite transactions.

New checks prove that:

- Upload persists the source and pending job without calling NLP, metadata,
  filtering, or translation. Regeneration similarly defers NLP/provider work.
- Prepared originals can be practiced while metadata inference is deliberately
  blocked; concurrent title edits and completed-sentence progress survive inference
  and completion. Regeneration keeps the same sentence IDs and progress.
- Failed language detection can retry from saved source. Missing models leave an
  actionable asynchronous error and recover after restoring the model and retrying.
- Translation retries reuse preparation instead of running NLP again. Failed AI
  regeneration retains previous vocabulary/drills.
- A fresh API lifespan resumes another owner's queued raw source. Existing queue
  concurrency and stale-worker response regressions continue to pass.
- The real browser shows saved source while preparation is held, then exposes the
  typing canvas on polling. The test delays the API presentation of preparation;
  backend tests independently verify the actual worker checkpoints.
- Migration upgrade/adoption and compatibility rollback preserve library/source
  data and refuse unsafe rollback of unprepared uploads.

An additional real-process smoke started an isolated API with embedded consumption
disabled, saved a synthetic German upload, and started two CLI workers. One attempt
prepared the original and reported the expected offline enrichment failure; both
workers exited cleanly on SIGTERM. No live provider request or paid spend was needed.

The previous SQLite unclosed-connection ResourceWarnings remain separate. Delivery
continues to be at least once: a crash after an external request may repeat that
request. Original practice requires sentence preparation; the HTTP response itself
does not wait for it. PostgreSQL/staging recovery and language-teaching quality remain
next acceptance gates.
