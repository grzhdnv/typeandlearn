# ADR-0004: Offline Lexical Resources and Dictionary Licensing

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

TypeAndLearn provides instantaneous hover definitions, word frequency ranking, and translation hints during typing drills. 

Relying on external commercial dictionary APIs (such as Oxford, Collins, or Linguee) introduces runtime HTTP latency, unpredictable ongoing API costs, rate limits, and network failure modes during core typing interaction. Conversely, bundling unverified or scraped proprietary dictionaries risks intellectual property infringement.

## Decision

1. **Local, Offline-First Lexical Store**:
   - Package bilingual and monolingual lexical databases locally as optimized SQLite databases or indexed pre-seeded database tables.
   - Lookups must execute locally in sub-millisecond time without blocking the typing interface or frontend render thread.

2. **Approved Open-Source Data Sources**:
   - **FreeDict Project**: Standard TEI-derived dictionaries licensed under GNU GPL / CC-BY-SA with clear machine-readable exports.
   - **Wiktionary-Derived Corpora**: Structured lemma, definition, and part-of-speech datasets (e.g., via Wiktextract / Kaikki) distributed under Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0).
   - **Official spaCy Language Models**: Pinned releases for French, German, Spanish, Italian, and English (distributed under MIT or open source licenses).

3. **Attribution and Compliance**:
   - Compile a dedicated `ATTRIBUTIONS.md` document citing the license, version, and copyright holders of every bundled dictionary and dataset.
   - Maintain clear separation between application business logic and CC BY-SA lexical database files to avoid viral licensing ambiguities.

4. **Prohibited Practices**:
   - Scraping proprietary web dictionaries without explicit commercial distribution licenses is strictly banned.

## Consequences

- **Positive**: Sub-millisecond lookup latency, zero per-lookup API costs, full offline capability, and legal safety.
- **Negative**: Bundle size increases to accommodate local dictionary databases; dataset updates must be managed via scheduled release assets.
