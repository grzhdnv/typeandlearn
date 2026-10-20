# ADR-0005: Groq-First LLM Routing, Failover, and Spend Governance

- **Status**: Accepted; local implementation verified 2026-10-19
- **Date**: 2026-08-30; provider policy revised 2026-10-19

## Decision

Core library and typing practice remain available without provider credentials.
All four enrichment tasks share the same provider transport and database ledger.

- Primary: Groq `openai/gpt-oss-120b`, low reasoning, native strict JSON schema.
- Fallback: DeepSeek `deepseek-flash`, thinking disabled, typed tool output.
- Challenger: Groq `qwen/qwen3.8-27b`, preview; explicit schema profile bridges the
  pinned SDK's older capability registry. It is available as a configuration choice,
  not an extra automatic fallback.
- Provider identifiers remain configurable. Missing primary credentials allow the
  configured fallback to serve requests. An invalid credential or request does not
  trigger paid fallback.

Transient HTTP 408/429/500/502/503/504 and typed transport/SDK connection errors
allow fallback. Provider reset headers and Retry-After establish a shared cooldown.
Local Groq quota contention waits at most ten seconds before selecting fallback;
an upstream transient failure can select fallback immediately. There is no SDK
retry stack. One bounded schema-repair attempt is allowed and accounted separately.
Exhausted application or paid budgets terminate the attempt without further routing.

## Quotas and spending

The supplied account limits are 30 requests/minute, 1,000 requests/day,
8,000 tokens/minute, and 200,000 tokens/day. Defaults reserve 20% headroom:
24 RPM, 800 RPD, 6,400 TPM, and 160,000 TPD. The application's Groq limits aggregate
all configured models conservatively. Actual remaining/reset headers can restrict
these further. Live Qwen testing also encountered an output-token-per-minute limit
not visible in the screenshot; upstream 429 handling remains necessary.

DeepSeek has user-approved **$0.50/day and $5/month** limits across this application's
API and workers, using UTC calendar windows. Both limits must admit a request before
network dispatch. Reservations use a conservative UTF-8 byte input bound and the
maximum output size; known usage refunds unused allowance. Timeouts, missing usage,
and abandoned requests retain their reservation until its window expires. Zero
budget blocks paid requests. Account deletion anonymizes reservations rather than
resetting global spend.

The defaults also cap each request at 32,000 serialized bytes and 2,048 output
tokens, and each owner at 50,000 actual plus reserved tokens/day. SQLite uses an
immediate transaction; PostgreSQL uses a transaction advisory lock. PostgreSQL
concurrency has not yet been integration-tested. Separate databases or other apps
using these keys are outside this ledger's control.

DeepSeek estimates use conservative peak USD rates per million tokens: input cache
miss $0.30, cache hit $0.006, output $1.20. Groq is accounted at zero for this free-tier
account. These are configurable estimates, not a provider billing integration;
price or tier changes require updating configuration.

Every real response records the actual returned provider/model and token usage,
including metadata, filtering, fallback, and schema repair. The quota ledger stores
no learning content. Existing translation caching remains keyed by languages,
sentence hash, and prompt version; multilingual prompt changes bump the version.

## Validation and limits

See [the synthetic comparison](../provider-evaluation-2026-10-19.md). Automated
regressions cover routing, serialization, parallel reservations, daily/monthly
limits, unknown billing, usage reconciliation, migrations, and privacy. Live models
are never called by CI. Full semantic hint coverage, batched transport, durable
job dispatch, and production PostgreSQL acceptance remain follow-up work.

## Sources

- [Groq models](https://console.groq.com/docs/models)
- [Groq structured outputs](https://console.groq.com/docs/structured-outputs)
- [Groq rate limits and headers](https://console.groq.com/docs/rate-limits)
- [DeepSeek prices](https://api-docs.deepseek.com/quick_start/pricing/)
- [DeepSeek thinking controls](https://api-docs.deepseek.com/guides/thinking_mode/)
