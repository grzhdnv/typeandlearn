# OpenRouter free-model evaluation — 20 October 2026

Keep Groq GPT-OSS 120B as primary and capped DeepSeek Flash as fallback.
Nemotron Ultra 550B is a useful optional free challenger, but this sample does not
justify promoting it before hint validation. Dots was faster but made more hint
errors. Nemotron Super's current free endpoint returned upstream 404 errors.

## Final comparison: reasoning disabled

Each model received the same five synthetic translations (German, French, Italian,
Spanish, English), French metadata, and a request for five Spanish exercises as the
[19 October baseline](provider-evaluation-2026-10-19.md). No library text was sent.
All model IDs were checked against the live catalog for zero prices immediately
before inference. Paid model/provider fallback and SDK retry stacks were disabled;
one application schema repair remained available and separately accounted.

| Model | Total / active parameters | Usable typed tasks | Median task time | Exercises | Reported tokens / cost |
| --- | --- | --- | --- | --- | --- |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 550B / 55B | 7/7, first attempt | 3.83 s | 5; 25.29 s | 9,053 / $0 |
| `dots-studio/dots-3-note-preview:free` | 280B / 16B | 7/7, first attempt | 2.42 s | 5; 9.55 s | 5,957 / $0 |
| `nvidia/nemotron-3-super-120b-a12b:free` | 120B / 12B | 0/7: upstream 404 | Not comparable | None | 0 / $0 |

The final run made 21 dispatched requests, including seven nonbillable 404s;
successful replies used **15,010 reported tokens at $0**. No quota wait occurred
in this final run. Task times include public catalog preflight and local dispatch,
so they are not pure model latency. Seven cases per model are a spot check, not a
statistical ranking or sustained-load test.

[Frozen final outputs, final response bodies, and per-attempt accounting](evaluations/openrouter-2026-10-20-final.json)
exclude credentials, upstream raw account identifiers, and reasoning text. The
[catalog/quota/configuration snapshot](evaluations/openrouter-2026-10-20-final.preflight.json)
records model capabilities, free prices, and run-only limits.

## Language and hint quality

Ultra and Dots preserved the principal meaning of all five full translations,
including the French counterfactual and Italian idiom. Both generated five coherent
Spanish sentences. Their French difficulty estimates differed: Ultra B2, Dots A2;
these were not checked against a CEFR gold standard.

Ultra grouped German `stehe … auf` and Spanish `Se me olvidaron` appropriately.
Its French hints split `j'avais` into `j'` and `avais`, left `tôt` with an empty
hint, and split Italian `l'ora`. Those outputs do not match the current UI's
whole-word hint lookup. Ultra's English response also included two unused extra
fields, permitted by the current Pydantic response model.

Dots included German `früh` in a group whose hint was only “get up,” losing “early”
in the hint even though the full translation was correct. Its Italian hints mapped
`Non` to “I” and reduced `rivederti` to “see.” Its Spanish translation omitted `me`
from the hint groups. The first generated exercise mapped `quiero` to the Spanish
word itself and `olvidar` to “want to.” Several exercise hint entries contained
whole phrases such as `de la` rather than separate words, making them unavailable
at the UI's individual-word cursor positions.

A mechanical audit using the current UI's matching rules found **3 unavailable or
empty hints across 82 word positions for Ultra**, and **14 across 89 for Dots**
(five source sentences plus five exercises per model). This measures lookup
availability, not semantic correctness; the Dots meaning errors above are additional.
See [the audit](evaluations/openrouter-2026-10-20-hint-audit.json).

Super's seven calls reached OpenRouter but its Nvidia backend returned 404 with
an unavailable-function error. These are availability failures, not evidence about
Super's language ability. The advertised catalog alone is insufficient acceptance.

At the user's request, Super was retried after the API key settings were edited.
The key preflight succeeded (32 used / 1,000 allowed free requests); all seven
fresh cases again returned 404 “Provider returned error” from Nvidia, with zero
tokens and $0 reported cost. See the [retry outputs](evaluations/openrouter-2026-10-20-super-retry.json)
and [retry preflight](evaluations/openrouter-2026-10-20-super-retry.preflight.json).
The repeated result leaves Super unavailable under the current routing/settings;
it does not isolate which upstream or account setting is responsible.

## Why earlier probes failed

The initial key was a management key. `/api/v1/key` returned 200, but all 21 cases
plus one diagnostic inference returned 401. The user replaced it with a regular
inference key. The runner now rejects management keys before inference and stops on
local or upstream 401/402/403, including failures with no ledger row.

The first real-key run shared a UTC-day token allowance with the previous evening's
benchmarks and hit the evaluation owner's 50,000-token limit. Default reasoning
also exposed Ultra tool-call text serialized as ordinary content. Dots spent almost
all 2,048 output tokens reasoning, producing no final answer on three completed
translation probes. A fourth Dots request was interrupted, retaining its conservative
unknown-usage reservation. The resumed runner preserves prior failures and skips
successful cases, rather than repeating everything after an interruption.

The final adapter explicitly requests `reasoning.enabled=false`; all three catalog
entries advertise optional reasoning. With this setting, Ultra and Dots completed
all final cases without repair. The final run used temporary **100 RPD and 150,000
owner tokens/day** evaluation overrides so previous failed/probe history remained
accounted without changing app defaults. The key endpoint at final preflight
reported 18 used / 1,000 allowed free requests. Earlier key snapshots reported a
50-request tier; the recorded current allowance controlled the final run. No credit
purchase or account setting was performed by the agent.

Across all OpenRouter attempts in this session, including authentication failures,
probes, and interruption, the shared ledger contained 68 calls after the Super retry: 31 with returned
usage, 36 failed without usage, and one unknown. Returned usage totaled **45,980
tokens at $0**; the unknown call retains a 3,477-token reservation. Final-run totals
above exclude these earlier probes. Raw failures remain available in the matching
`openrouter-2026-10-20-*` files under `evaluations/`.

## Adapter policy and reproduction

The opt-in adapter reuses the existing SDK, transport, and database governor.
It requires explicit `:free` IDs, zero catalog prices, supported output parameters,
and optional reasoning. Every inference checks the public catalog. Requests cap
prompt, completion, and per-request prices at zero, disable provider fallback,
disable reasoning, and require parameter support. Ultra uses typed tool output;
Dots and Super use native strict JSON schema. Every inference/repair reserves
capacity and reconciles returned models, usage, and reported cost.

OpenRouter's application defaults remain **16 RPM / 40 RPD**, with bounded waits,
shared cooldowns, Retry-After, and epoch reset handling. These quotas are separate
from Groq and never consume DeepSeek spending budgets. The account's free allowance
can also be consumed by other applications; the local ledger cannot govern them.

With a regular `OPENROUTER_API_KEY` in the ignored `.env`, run from the repo root:

```bash
.venv/bin/python scripts/evaluate_providers.py --openrouter-free \
  --output /private/tmp/typeandlearn-openrouter-evaluation.json
# Resume unfinished cases in that file, retaining earlier failures:
.venv/bin/python scripts/evaluate_providers.py --openrouter-free --resume \
  --output /private/tmp/typeandlearn-openrouter-evaluation.json
```

For exact final-run settings, use the run-only overrides recorded above and in the
preflight artifact. Ordinary runs retain the lower application defaults. Live
comparisons remain opt-in and never run in CI.

## Data handling and recommendation

OpenRouter prompt/response retention is opt-in, while request metadata is retained.
Underlying free-provider retention/training policies vary. The comparison used
synthetic content and existing account privacy settings; it did not change toggles
or clear these providers for personal learning texts.

Ultra deserves the next optional free-fallback experiment after Groq, provided
provider data handling is acceptable and hint validation/normalization is added.
It does not show a quality or speed advantage over the working Groq baseline in
this small sample. Dots' hint errors make it a weaker learning-app choice despite
its lower latency. Super should remain out of automatic routing until its endpoint
works. Current default routing stays unchanged.

## Verification

`npm run check` uses isolated SQLite and blank Groq, DeepSeek, and OpenRouter keys:
Ruff, Pyright, compilation, 91 backend tests, frontend typecheck/build, and 27 frontend
tests. All 21 isolated Chromium tests passed earlier in this implementation session.
Existing SQLite unclosed-connection ResourceWarnings remain. PostgreSQL concurrency
and production acceptance remain unverified.

## Official sources checked

- [Live model catalog](https://openrouter.ai/api/v1/models)
- [Pricing and free-tier limits](https://openrouter.ai/pricing)
- [Limits and quota endpoint](https://openrouter.ai/docs/api_reference/limits)
- [Provider routing and price caps](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Reasoning controls and token budgets](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
- [Data collection](https://openrouter.ai/docs/guides/privacy/data-collection)
- [Management keys](https://openrouter.ai/docs/guides/overview/auth/management-api-keys)
