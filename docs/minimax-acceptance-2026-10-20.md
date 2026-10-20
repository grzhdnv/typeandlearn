# MiniMax and hint acceptance — 20 October 2026

Technical acceptance passed for the optional Groq → MiniMax → capped DeepSeek
chain. Default routing remains Groq/DeepSeek. MiniMax's content-use terms and the
remaining teaching-quality limits are documented below; Jev remains deferred.

## Implemented

The typing UI now normalizes surrounding Unicode punctuation, NFC accents,
apostrophe variants, and hyphen variants. It matches hints by word occurrence and
grapheme cursor position, so the same word can have different meanings at different
positions. Noncontiguous groups such as `stehe … auf` highlight their actual spans.
Legacy phrase-valued entries and single hints for repeated words remain readable.

The provider layer normalizes harmless phrase entries, spelling variants, and
unambiguous casing. Within an existing meaning group it can join a split
apostrophe word. It never merges unrelated meanings or substitutes dictionary
lemmas for source forms. Missing, duplicate, unknown, or empty hints trigger one
accounted repair. Repair feedback identifies the exercise and missing source-word
positions without putting learning words in new log messages. Every occurrence
must be represented, including repeated articles. Exercises must have five source
sentences with nonempty English translations and complete hints.

Exhausted schema/hint repair can select the next configured provider. HTTP
400/401/402/403/404/422 remain permanent; bad credentials and exhausted application
or paid budgets do not trigger a paid network request. All retries and fallbacks
continue through the shared governor. No SDK retry stack was added.

Five fully hinted drills have a separate default output allowance of **4,096
tokens** (`LLM_PRACTICE_MAX_OUTPUT_TOKENS`); translations/metadata/filtering retain
2,048. Actual request caps feed the same quota/spend reservation logic, including
the approved DeepSeek $0.50/day and $5/month limits. Prompt/cache version is now
`v3-validated-hints`, so new enrichment does not reuse older unvalidated cache rows.
Existing library records were not bulk-rewritten.

## Real service acceptance

The opt-in [runner](../scripts/accept_minimax.py) creates five self-composed texts,
one in each supported language. Each has two sentences, including quotation marks,
curly apostrophes, repeated words, inverted question marks, subordinate clauses,
and idiomatic constructions. It uses real spaCy, metadata, LLM filtering,
translation, exercise generation, temporary SQLite learning storage, cache writes,
and a fresh repository readback. Only dictionary lookups are mocked. The real
shared provider ledger accounts for every inference. No personal texts are read.

| Language | Saved translations | Saved exercises | Final attempts | End-to-end time |
| --- | --- | --- | --- | --- |
| German | 2 | 5 | 5, no repair | 25.79 s |
| French | 2 | 5 | 5, no repair | 25.35 s |
| Italian | 2 | 5 | 5, no repair | 22.54 s |
| Spanish | 2 | 5 | 5, no repair | 17.02 s |
| English | 2 | 5 | 5, no repair | 13.36 s |

All five reached `processed` / `completed` and round-tripped through a new service
instance unchanged. All four provider task types ran: 5 metadata, 5 filtering,
10 translation, and 5 exercise calls. The final run used **36,571 returned tokens,
$0 reported cost, and 25 dispatched calls**, with no repairs or paid fallback.

The actual frontend `buildHintSpans` function was run against all **35 saved
sentences**: **353 word positions, zero unavailable/empty hints**. This audit checks
mechanical availability, not semantic correctness. Five-language Playwright cases
also verified the hint at the actual typing cursor, plus repeated-word meanings.

- [Final saved data, response diagnostics, and usage](evaluations/minimax-acceptance-2026-10-20-final.json)
- [Final model/quota snapshot](evaluations/minimax-acceptance-2026-10-20-final.preflight.json)
- [Frontend matcher audit](evaluations/minimax-acceptance-2026-10-20-ui-audit.json)
- [Initial failures](evaluations/minimax-acceptance-2026-10-20-initial.json)

The initial 2,048-token drill run accepted German/Spanish/English but failed French
and Italian. German/French exhausted output space on a first exercise attempt;
French's repair then omitted a repeated article, while Italian's repair repeated
a lemma (`vedere`) in place of the actual source form (`vedo`). After the larger
drill allowance and more targeted repair instructions, all five complete flows
passed on their first attempts. The first failures remain recorded, not overwritten.

The acceptance run uses temporary **200 RPD / 150,000 tokens per evaluation owner**
limits to include accumulated benchmark history. App defaults remain 16 RPM /
40 RPD / 50,000 owner tokens/day. The provider key's final preflight showed 94 used
of 1,000 free daily requests. Capacity waits may run for up to 65 seconds in this
opt-in benchmark; normal application waits remain ten seconds. The preflight's
2,048-token field describes non-practice tasks; the run used the new 4,096-token
drill cap. Future snapshots also record the drill cap and prompt version explicitly.

Reproduce without touching learning-library data:

```bash
OPENROUTER_RPD=200 DAILY_TOKEN_LIMIT=150000 .venv/bin/python scripts/accept_minimax.py \
  --output /private/tmp/typeandlearn-minimax-acceptance.json
# Limit an investigation to one language:
OPENROUTER_RPD=200 DAILY_TOKEN_LIMIT=150000 .venv/bin/python scripts/accept_minimax.py \
  --language French --output /private/tmp/typeandlearn-minimax-french.json
```

## Teaching quality and content scope

A manual spot review found the ten full translations preserve their source
meaning. Some generated scenarios remain contrived, and French exercise wording
such as `J'ai su acheter du pain…` is awkward for general-purpose practice.
Metadata CEFR estimates (A1/A2 here) remain unvalidated and can understate the
source grammar's difficulty. Mechanical/schema acceptance does not establish a
pedagogically reviewed corpus or a production-quality language assessment.

MiniMax's [API terms](https://platform.minimax.io/protocol/terms-of-service) permit
using inputs and generated content to maintain, develop, and improve services.
Its [privacy policy](https://platform.minimax.io/protocol/privacy-policy) describes
processing input/output and retaining personal data as needed for stated purposes
or applicable law. These are not a blanket no-training or zero-retention guarantee.
[OpenRouter provider-logging documentation](https://openrouter.ai/docs/guides/privacy/provider-logging)
explains account/request controls for providers that may train; the default chain
has not been changed to send arbitrary user learning material through MiniMax.

For optional use with suitable non-sensitive study material, the tested setting is:

```dotenv
FALLBACK_MODELS=["openrouter:minimax/minimax-m3.1-flash:free","deepseek:deepseek-flash"]
```

The primary remains Groq. `.env.example` documents this opt-in choice and the content
use terms. This work does not enable MiniMax globally or alter account privacy
settings. The user's next provider decision is whether that content scope and
policy are acceptable; implementation and technical verification are ready.

## Verification and remaining work

`npm run check` passed: Ruff, Pyright, compilation, **102 backend tests**, frontend
build/type checks, and **31 frontend tests**. **27 Chromium tests** passed, including
all existing practice/review/navigation regressions and five-language hint display.
Checks used temporary SQLite storage with all provider keys blank. New offline
transport tests cover bounded coverage repair, the Groq/MiniMax/DeepSeek chain,
OpenRouter quota fallback, permanent credentials errors, and zero paid budget.
The prior SQLite unclosed-connection ResourceWarnings remain.

Next engineering work is the API/worker's shared dispatch/claim path, broader
staging/recovery acceptance, and future teaching-quality improvements. No new SDK
or dependencies were installed, no paid OpenRouter calls were made, and Jev was
not added. PostgreSQL concurrency and hosted production acceptance remain open.
