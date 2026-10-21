# Provider check — 19 October 2026

Keep Groq `openai/gpt-oss-120b` as primary and DeepSeek `deepseek-flash` as fallback.
Qwen `qwen/qwen3.8-27b` is a fast optional challenger, but its preview status and
additional output-token limit make it a less predictable default for this account.

## Small live sample

Each model translated five self-composed sentences (German, French, Italian,
Spanish, English), inferred French metadata, and generated five Spanish exercises.
The translations exercise separable verbs, counterfactuals, an idiom, accidental
forgetting, and past perfect continuous. Only synthetic content was sent.

| Model | Final schema-valid tasks | Median task time, including quota waits | Observations |
| --- | --- | --- | --- |
| Groq GPT-OSS 120B | 7/7 | 1.26 s | Natural translations, five Spanish exercises, correctly grouped German separable verb |
| Groq Qwen 3.8 27B | 7/7 | 0.43 s | Fast final strict-schema run; some exercise wording was awkward |
| DeepSeek Flash | 7/7 | 1.31 s | Natural translations and five exercises; useful multi-word hint grouping |

Both Groq runs included a roughly 58-second local quota wait on one task; the
benchmark allows 65 seconds to keep its results provider-specific. The application
instead waits at most ten seconds for local capacity and can then use DeepSeek.
These are seven-task spot checks, not a throughput benchmark or a statistical
quality ranking. Schema success does not guarantee linguistic quality.

All models preserved the five sentences' main meanings. German's `stehe … auf`
was grouped correctly, and Italian's idiom became “I can't wait to see you again.”
The metadata difficulty estimate varied: GPT-OSS rated the French
counterfactual A2, DeepSeek B1, and Qwen B2; this was not validated against a CEFR gold standard.
DeepSeek sometimes put a whole phrase into one hint `words` entry (e.g. `dentro de`)
instead of separate word entries. Complete semantic hint coverage and token
normalization remain follow-up quality work.

The pinned SDK initially lacked Qwen's native-schema capability and strict schema
transformer. An explicit profile and a regression test now cover both. A separate
tool-output probe received one upstream 429 citing a 1,000 output-token/minute
allowance, which was not shown in the supplied screenshot. Shared cooldowns honor
such responses; the application should not assume the screenshot lists every gate.

## Application flow and cost

A real DeepSeek fallback check also completed a synthetic French text through local
spaCy preprocessing, saved translation, five saved exercises, and the completed
state. Groq capacity was deliberately set below one request's reservation to select
fallback. Learning data lived in a temporary database; only dictionary lookup was
mocked. Provider usage went through the real shared ledger.

The entire evaluation, including adapter probes and this fallback flow, made nine
DeepSeek requests. Its conservative peak-rate estimate was **$0.004437** (under
half a cent). Groq used its free allowance. The ledger, rather than a guessed model
label on the task result, supplied these figures.

## Reproduction and acceptance

From the repository root, with configured keys:

```bash
uv run python scripts/evaluate_providers.py
# Or isolate one provider:
uv run python scripts/evaluate_providers.py --model deepseek:deepseek-flash
```

This is explicitly a live, potentially billable command. It uses shared application
quota and spending reservations and never reads library texts. Results default to
`/private/tmp/typeandlearn-provider-evaluation.json`.
[The frozen final outputs](evaluations/2026-10-19-providers.json) contain only the
synthetic sample. Failed adapter-probe payloads and account identifiers are excluded.

Verification: lint, Pyright, Python compilation, frontend build/type checks,
81 backend tests, 27 frontend tests, and 21 isolated Chromium regressions passed.
Existing SQLite unclosed-connection ResourceWarnings remain in the backend suite;
PostgreSQL concurrency and hosted production acceptance were not tested here.

Provider configuration, limits, price sources, and remaining scope are recorded in
[ADR-0005](decisions/0005-llm-routing-and-spend.md).
