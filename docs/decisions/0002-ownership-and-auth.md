# ADR-0002: Ownership Foundation and Authentication Architecture

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

In the initial prototype, all stored texts, sentences, and progress records exist globally in a shared SQLite database without multi-tenant partitioning or ownership markers. Retrofitting ownership onto an existing schema late in development frequently introduces breaking migrations, data integrity hazards, and accidental authorization bypass vulnerabilities.

While full user authentication (login screens, sessions, OIDC providers) is scheduled for Milestone M4, the data architecture must be multi-tenant safe from the outset.

## Decision

1. **Mandatory Ownership Columns**:
   - Every persisted entity that belongs to a user (`Text`, `Sentence`, `PracticeSession`, `BackgroundJob`, `WeakWordMetric`) must declare a non-nullable `owner_id: str` field in its schema definition.
   - All repository queries and data mutations must require and filter by `owner_id`. Cross-user data leakage at the query layer is prohibited.

2. **Decoupled Auth Adapter & Local Development Default**:
   - Decouple identity resolution using a pluggable FastAPI dependency (`get_current_owner_id`).
   - During Milestone M0–M3 local prototyping, the provider defaults to a deterministic local user constant (`"owner_local_default"`).
   - In Milestone M4, this dependency will resolve JWT/session claims from a secure managed identity provider (e.g., Clerk, Supabase Auth, or standard OIDC) without requiring schema alterations to business tables.

3. **Database Constraints & Indices**:
   - Compound indexes must lead with `(owner_id, ...)` for high-frequency queries (such as listing texts or querying session metrics).

## Consequences

- **Positive**: Prevents costly structural migrations when authentication is introduced. Guarantees that query APIs and repositories are multi-tenant aware from the beginning.
- **Negative**: Adds minor boilerplate to local testing fixtures, which must supply an explicit `owner_id`.
