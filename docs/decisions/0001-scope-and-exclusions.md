# ADR-0001: Scope and Production Non-Goals

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

TypeAndLearn turns source texts into guided language-learning typing practice. As the project transitions from a local proof-of-concept to a robust multi-user application, there is a risk of feature bloat by attempting to emulate every dimension of popular typing platforms (such as Monkeytype) or expansive language platforms (such as Duolingo).

We need clear boundaries to focus our engineering effort on proving the core learning loop: input text ingestion, deterministic typing drills, contextual lexical hints, and durable private learning analytics.

## Decision

1. **In-Scope for Production v1**:
   - High-fidelity text intake and ingestion (plain text, markdown).
   - Deterministic typing practice engine with accurate WPM, accuracy, caret movement, and Unicode/IME compatibility.
   - Multilingual offline tokenization, lemmatization, and filtering across five target languages (German, French, Italian, Spanish, English).
   - Asynchronous LLM enrichment (translation hints, contextual sentence generation) with strict spend and rate limits.
   - Private, durable user progress, error classification, and weak-word tracking.
   - Self-service data export and deletion compliant with GDPR/CCPA.

2. **Explicit Non-Goals for Production v1**:
   - **Competitive Leaderboards & Social Feeds**: No public rankings, friend feeds, or social sharing.
   - **Anti-Cheat Infrastructure**: No keystroke obfuscation, browser lockouts, or heuristic bot-detection networks.
   - **Extensive Theme Marketplaces & Sound Customizers**: Clean, accessible default design system with minimal high-contrast/reduced-motion toggles rather than arbitrary custom themes.
   - **Complex Gamification**: No streaks, badges, currency economies, or loot mechanics.

## Consequences

- **Positive**: Eliminates substantial moderation, anti-cheat maintenance, and complex social state machines. Keeps database schemas and API boundaries clean.
- **Negative**: Users looking for competitive or gamified typing experiences will not find them in v1.
