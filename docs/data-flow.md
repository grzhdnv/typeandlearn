# TypeAndLearn Data Flow Working Map

Updated: 30 August 2026

This document represents the app as layered, editable bullet points. It separates
implemented behavior from the proposed production flow so design ideas are not
mistaken for current behavior.

## How to annotate this document

- Node identifiers such as `UI-1` and `BE-2` are stable references.
- An arrow such as `UI-1 -> API-1` means data moves from the first node to the
  second.
- `[current]` describes behavior implemented in the repository.
- `[external]` identifies a network or provider boundary.
- `[target]` describes a proposed production behavior.
- Add comments under an **Annotations** bullet without changing the node id.

## Current system layers

- **Layer 1 — Browser application** `[current]`
  - **UI-1 — Library page**
    - Inputs:
      - Text pasted or entered by the user.
      - Optional title, author, language, and processing choices.
      - Search and filter input.
    - Sends:
      - `POST /api/texts` to create a text.
      - Read, update, and delete requests for library records.
    - Receives:
      - Text summaries for the library.
      - Upload, update, and deletion results.
    - Next nodes:
      - `UI-1 -> API-1`
    - **Annotations:**
      - [ ] Add notes here.
  - **UI-2 — Practice page**
    - Inputs:
      - Selected text id.
      - Original-text, frequency-word, or generated-practice mode.
    - Sends:
      - `GET /api/texts/{id}` to load practice data.
      - Progress updates containing completed sentence indices.
      - Reset and word-regeneration requests.
    - Receives:
      - Text, sentences, translations, word frequencies, generated sentences,
        dictionary data, and processing status.
    - Behavior:
      - Starts `UI-4` while the record status is `processing`.
      - Supplies selected content to `UI-3`.
    - Next nodes:
      - `UI-2 -> API-1`
      - `UI-2 -> UI-3`
      - `UI-2 -> UI-4`
    - **Annotations:**
      - [ ] Add notes here.
  - **UI-3 — Typing interface**
    - Inputs:
      - Target sentence or practice text.
      - Keyboard input through a hidden browser input.
      - Hint keyboard shortcuts.
    - Deterministic behavior:
      - Compares input characters to target characters by position.
      - Highlights correct and incorrect characters locally.
      - Declares completion when input length reaches target length.
    - Outputs:
      - Completion event to `UI-2`.
      - No durable attempt metrics beyond the resulting completed index.
    - Next nodes:
      - `UI-3 -> UI-2 -> API-1`
    - **Annotations:**
      - [ ] Define desired correction and completion rules.
      - [ ] Define which session metrics should be saved.
  - **UI-4 — Processing poller**
    - Trigger:
      - `UI-2` receives a record whose status is `processing`.
    - Behavior:
      - Repeats `GET /api/texts/{id}` every two seconds.
      - Stops after the status changes or the page is left.
    - Next nodes:
      - `UI-4 -> API-1 -> DB-1 -> UI-2`
    - **Annotations:**
      - [ ] Decide whether production should keep polling or use server events.

- **Layer 2 — HTTP API** `[current]`
  - **API-1 — FastAPI text routes**
    - Inputs:
      - HTTP requests from `UI-1`, `UI-2`, and `UI-4`.
    - Responsibilities:
      - Parse and validate request schemas.
      - Call `BE-1` for text operations.
      - Schedule `BE-2` through FastAPI background tasks after upload, reset, or
        regeneration.
      - Serialize application records into HTTP responses.
    - Next nodes:
      - `API-1 -> BE-1`
      - `API-1 -> BE-2`
    - **Annotations:**
      - [ ] Add notes here.

- **Layer 3 — Backend orchestration** `[current]`
  - **BE-1 — Text service**
    - Synchronous intake responsibilities:
      - Send input to `DET-1` for sanitization.
      - Send sanitized text to `DET-2` for sentence splitting and frequency
        extraction.
      - Optionally call `LLM-1` for filtering.
      - Call `LLM-1` when title or author metadata must be inferred.
      - Create the parent text and child records through `DB-1`.
      - Set the text status to `processing`.
    - Read and mutation responsibilities:
      - Load texts and titles.
      - Update metadata and completed sentence indices.
      - Delete, reset, and regenerate text data.
    - Important boundary:
      - Optional LLM filtering and metadata inference happen before the upload
        response, so provider latency can delay intake.
    - Next nodes:
      - `BE-1 -> DET-1 -> DET-2 -> DB-1`
      - `BE-1 -> LLM-1` when optional AI work is requested.
    - **Annotations:**
      - [ ] Identify responsibilities to move out of this service.
  - **BE-2 — In-process background enrichment**
    - Triggers:
      - Successful upload.
      - Reset or word-regeneration request.
      - Application startup finds records still marked `processing`.
    - Reads:
      - Pending sentences and word-frequency records from `DB-1`.
    - Work:
      - Translate sentences through `LLM-1`.
      - Generate practice sentences through `LLM-1`.
      - Fetch definitions for frequent words through `DICT-1`.
    - Writes:
      - Sentence translations.
      - Generated practice sentences.
      - Dictionary translations and definitions.
      - Final text status.
    - Important boundary:
      - The task is not a durable queue job. Process interruption can leave work
        incomplete until startup recovery runs.
      - Independent enrichment failures can be obscured by the single final text
        status.
    - Next nodes:
      - `BE-2 -> LLM-1`
      - `BE-2 -> DICT-1`
      - `BE-2 -> DB-1`
    - **Annotations:**
      - [ ] Define which enrichment operations may fail independently.
      - [ ] Define retry and cancellation behavior.

- **Layer 4 — Deterministic processing** `[current]`
  - **DET-1 — Text sanitizer**
    - Receives raw user text from `BE-1`.
    - Normalizes and cleans the text without an LLM.
    - Sends sanitized text to `DET-2`.
    - **Annotations:**
      - [ ] Record required normalization and size-limit rules.
  - **DET-2 — spaCy preprocessing**
    - Splits text into paragraphs and sentences.
    - Extracts word frequencies using the configured language pipeline.
    - Sends structured results back to `BE-1` for persistence.
    - **Annotations:**
      - [ ] Define supported-language behavior when a model is unavailable.
  - **DET-3 — Browser typing comparison**
    - Compares typed and expected characters by position.
    - Produces immediate visual state without a network or LLM call.
    - **Annotations:**
      - [ ] Replace this with a versioned session reducer before production.

- **Layer 5 — LLM enrichment** `[current]`
  - **LLM-1 — Structured LLM service**
    - Receives typed task inputs from `BE-1` or `BE-2`.
    - Uses Pydantic schemas to validate structured responses.
    - Applies service-level retry behavior.
    - Supports:
      - Metadata inference.
      - Optional content filtering.
      - Sentence translation.
      - Practice-sentence generation.
    - Provider path:
      - `LLM-1 -> EXT-1`
    - **Annotations:**
      - [ ] Assign a versioned task name to each operation.
      - [ ] Define validation, time, token, retry, and cost budgets.
  - **EXT-1 — LLM providers** `[external]`
    - DeepSeek is the current default.
    - Groq can be configured but is not yet the implemented first-provider policy.
    - Provider availability, rate limits, latency, and output quality affect the
      upstream workflow.
    - **Annotations:**
      - [ ] Approve Groq-first fallback conditions.
      - [ ] Approve DeepSeek spend limits.

- **Layer 6 — Dictionary enrichment** `[current]`
  - **DICT-1 — Dictionary service**
    - Receives frequent words from `BE-2`.
    - Requests definitions from `EXT-2` using concurrent network calls.
    - Returns available results for persistence through `DB-1`.
    - **Annotations:**
      - [ ] Decide whether definitions are required for production v1.
  - **EXT-2 — Wiktionary REST API** `[external]`
    - Best-effort external source.
    - Availability and response shape are outside application control.
    - **Annotations:**
      - [ ] Select a pinned local dataset or explicitly omit definitions.

- **Layer 7 — Persistence** `[current]`
  - **DB-1 — Text repository**
    - Maps service operations to SQLModel reads and writes.
    - Uses SQLite locally and can use PostgreSQL.
    - Writes and reads the following records:
      - **DB-2 — Text record**
        - Source text and metadata.
        - Processing status.
        - Completed sentence indices.
      - **DB-3 — Sentence records**
        - Source sentences and translations.
      - **DB-4 — Word-frequency records**
        - Extracted words, counts, and dictionary enrichment.
      - **DB-5 — Practice-sentence records**
        - LLM-generated practice content.
    - **Annotations:**
      - [ ] Define ownership and retention requirements.
      - [ ] Define transactional boundaries and uniqueness constraints.

## Current end-to-end flows

- **Flow A — Add a text**
  - `User -> UI-1`
  - `UI-1 -> API-1`: raw text, metadata, language, and processing choices.
  - `API-1 -> BE-1`: validated upload request.
  - `BE-1 -> DET-1 -> DET-2`: cleaned text, sentences, and word frequencies.
  - `BE-1 -> LLM-1 -> EXT-1`: optional filtering or missing metadata.
  - `BE-1 -> DB-1`: text and child records with status `processing`.
  - `API-1 -> UI-1`: upload response.
  - `API-1 -> BE-2`: schedule enrichment after the response.
  - **Annotations:**
    - [ ] Add notes here.

- **Flow B — Enrich a text**
  - `BE-2 -> DB-1`: load pending sentences and frequent words.
  - `BE-2 -> LLM-1 -> EXT-1`: translations and generated exercises.
  - `BE-2 -> DICT-1 -> EXT-2`: dictionary definitions.
  - `BE-2 -> DB-1`: save enrichment and final status.
  - **Annotations:**
    - [ ] Define truthful partial-success behavior.

- **Flow C — Practice a text**
  - `User -> UI-2 -> API-1 -> BE-1 -> DB-1`: request full text data.
  - `DB-1 -> UI-2`: text, modes, enrichment, progress, and status.
  - `UI-2 -> UI-3`: selected target content.
  - `User -> UI-3 -> DET-3`: keyboard events and positional comparison.
  - `DET-3 -> UI-2`: completion event.
  - `UI-2 -> API-1 -> BE-1 -> DB-1`: persist completed sentence index.
  - **Annotations:**
    - [ ] Define the desired session-history and analytics flow.

- **Flow D — Recover interrupted work**
  - `Application startup -> DB-1`: find records whose status is `processing`.
  - `Application startup -> BE-2`: start a new in-process enrichment task.
  - `BE-2 -> DB-1`: overwrite or complete available enrichment fields.
  - **Annotations:**
    - [ ] Define idempotency rules before introducing a durable worker.

## Current status model

- **`processing`**
  - Can mean any combination of:
    - Deterministic records have been saved.
    - Translation is pending or running.
    - Practice generation is pending or running.
    - Dictionary lookup is pending or running.
    - A previous process stopped before finishing.
- **`processed`**
  - Indicates the background orchestration reached its end.
  - Does not provide a granular result for every enrichment operation.
- **Annotations:**
  - [ ] List any UI states the user should see between intake and full enrichment.

## Proposed production flow

- **Target principle 1 — Make deterministic practice the core path** `[target]`
  - `User -> API intake -> durable text record -> deterministic preprocessing`.
  - Mark the text `practice_ready` when its deterministic content is available.
  - Do not require an LLM or dictionary credential to add, browse, or practice
    original text.
  - **Annotations:**
    - [ ] Approve the minimum data required for `practice_ready`.

- **Target principle 2 — Treat enrichment as independent durable jobs** `[target]`
  - Create one versioned job per logical task:
    - `translate_sentence_v1`
    - `generate_hint_groups_v1`
    - `generate_practice_set_v1`
    - Optional `suggest_metadata_v1`
  - Persist job state before a worker executes it.
  - Give every job an idempotency key, retry budget, provider policy, and truthful
    terminal result.
  - Allow translation, generation, and dictionary enrichment to succeed or fail
    independently.
  - **Annotations:**
    - [ ] Define job priority and cancellation rules.

- **Target principle 3 — Route providers predictably** `[target]`
  - `Durable job -> deterministic validation -> cache lookup`.
  - On cache miss:
    - Use Groq first for capability-tested tasks.
    - Wait through normal Groq rate-limit resets when deadlines permit.
    - Use DeepSeek only for approved outage, deadline, capacity, or repair cases.
    - Never fall back for invalid input, bad credentials, or policy rejection.
  - `Provider response -> schema validation -> language/task validation -> result`.
  - **Annotations:**
    - [ ] Define per-task deadlines and fallback permissions.

- **Target principle 4 — Persist practice sessions, not just progress indices**
  `[target]`
  - `Browser input adapter -> versioned deterministic session reducer`.
  - `Session reducer -> immediate rendering and local metrics`.
  - `Completed session -> API -> practice session record`.
  - Save summaries such as:
    - WPM and raw WPM.
    - Accuracy and duration.
    - Error characters and words.
    - Hint usage and weak vocabulary.
  - Keep compact event traces optional and governed by retention policy.
  - **Annotations:**
    - [ ] Define privacy and retention for detailed input events.

## Design decisions to annotate next

- [ ] What is the earliest point at which an uploaded text should be practiceable?
- [ ] Which enrichment is required, optional, or excluded from production v1?
- [ ] Should users see per-stage status, a simple overall status, or both?
- [ ] What behavior should occur when only some sentences translate successfully?
- [ ] Which practice modes share one typing engine?
- [ ] What input events and session results must be persisted?
- [ ] When may DeepSeek be used after Groq?
- [ ] What are the maximum wait, retry, token, and cost budgets for each LLM task?
- [ ] Is polling acceptable for v1, or should status delivery use server-sent events?
- [ ] Which data belongs in application logs, metrics, traces, or nowhere?

