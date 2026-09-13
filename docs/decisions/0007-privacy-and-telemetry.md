# ADR-0007: Learning Privacy, Telemetry Redaction, and Data Retention

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

Language learners frequently paste personal correspondence, copyrighted literature, or study notes into TypeAndLearn. Inadvertently capturing user text in application logs, APM traces, or error tracking services creates severe privacy breaches, intellectual property liability, and GDPR/CCPA compliance failures.

## Decision

1. **Zero Raw Text in Logs & Telemetry**:
   - Application loggers, OpenTelemetry traces, and error handlers must NEVER log raw source text, sentence text, translation strings, or user keystroke streams.
   - For debugging and observability, logs may record:
     - Text length (`char_count`, `sentence_count`)
     - Truncated SHA-256 content hashes (e.g., `hash: "e3b0c442..."`)
     - Target language codes (`de`, `fr`, `es`, `it`, `en`)
     - Processing duration, status codes, and token usage counts.

2. **Structured JSON Logging & Correlation IDs**:
   - Output structured JSON logs directly to `stdout`.
   - Propagate standardized correlation headers: `request_id`, `owner_id` (opaque hash), `text_id`, and `job_id`.
   - Explicitly redact `Authorization`, cookie values, and LLM API keys before serialization.

3. **Data Ownership & Right to Erasure**:
   - Provide atomic text deletion: deleting a text immediately purges all associated sentences, dictionary caches, practice metrics, and pending background jobs via `CASCADE` database foreign keys.
   - Support machine-readable data export (`GET /api/user/export`) packaging all owned texts and practice history into a portable JSON archive.

## Consequences

- **Positive**: Strict GDPR/CCPA alignment; zero risk of leaking private user text into log collectors; clean observability and debugging traces via correlation IDs.
- **Negative**: Debugging specific NLP parsing or translation issues requires reproducing errors locally with synthetic fixtures rather than inspecting production logs.
