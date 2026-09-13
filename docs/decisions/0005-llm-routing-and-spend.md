# ADR-0005: Groq-First LLM Routing, Failover, and Spend Governance

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

The prototype initializes a DeepSeek client upon application import. This has significant drawbacks:
- Missing or invalid API keys prevent the backend from booting, blocking offline library browsing and local typing practice.
- There is no provider fallback or backpressure handling when an upstream provider throttles or outages.
- Lack of spend limits or content caching risks unbounded API billing under heavy text ingestion.

## Decision

1. **Decoupled Application Factory & Optional Providers**:
   - The backend must initialize and serve all core routes (library browsing, text intake, local spaCy processing, typing drills) even when no LLM API keys are configured.
   - LLM services are injected as an optional enrichment capability.

2. **Groq-First Routing with DeepSeek Failover**:
   - **Primary**: Route requests to Groq (`llama-3.3-70b-versatile` or current recommended tier) for ultra-low latency and low token costs.
   - **Fallback**: Upon receiving rate limits (HTTP 429) or transient provider errors (HTTP 502/503/504) from Groq, automatically fall back to DeepSeek (`deepseek-chat`).
   - The fallback circuit breaker incorporates exponential backoff and a hard monthly budget threshold.

3. **Strict Spend Controls & Cost Governance**:
   - Implement hard token caps per user per day.
   - Enforce maximum input token limits (e.g., 4,000 tokens per processing chunk) to prevent runaway costs from oversized inputs.
   - Cache LLM-generated translations in the database keyed by `(source_language, target_language, sentence_hash, prompt_version)` to avoid re-translating identical phrases.

4. **Structured Output & Prompt Registry**:
   - Centralize prompt templates in a versioned registry.
   - Enforce structured JSON responses using Pydantic schemas. If a provider returns malformed output, retry once with a temperature reduction before declaring a typed job failure.

## Consequences

- **Positive**: App remains 100% functional for offline/local use without API keys. Minimizes API latency and operating costs. Prevents billing surprises.
- **Negative**: Requires maintaining adapter configurations for two provider SDKs and schema validation logic.
