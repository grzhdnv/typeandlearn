# ADR-0006: Deterministic Typing Event Log and Metric Semantics

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

The prototype typing interface relies on naive character-index comparisons against target strings and completes automatically once `input.length == target.length`, regardless of unresolved mistakes. Furthermore:
- WPM and Accuracy values are non-functional placeholders (`--%`, `--`).
- Multilingual diacritics (e.g., German umlauts `ä, ö, ü`, French accents `é, è, ç`, Spanish `ñ`) can break when treated as separate UTF-16 code units.
- Input Method Editor (IME) composition events and dead keys can trigger premature error penalties.
- There is no immutable event trace from which typing velocity, pauses, bursts, and error clusters can be reliably recomputed.

## Decision

1. **Pure Reducer Architecture**:
   - Model the typing engine as a pure deterministic state reducer: `(TypingState, TypingEvent) -> TypingState`.
   - The engine is decoupled from browser DOM rendering and SolidJS signals, making it 100% testable in headless unit test runners.

2. **Immutable Input Event Stream**:
   - Every keystroke, deletion, paste, and composition action appends an immutable `InputEvent` to the session log:
     ```typescript
     interface InputEvent {
       type: "insert" | "delete" | "composition_end" | "restart";
       char?: string;
       timestampMs: number;
       cursorPosition: number;
     }
     ```
   - Session completion and metrics are derived purely from this deterministic event log.

3. **Standardized Typing Metrics**:
   - **Net WPM**: Standard formula based on normalized word length (5 characters):
     $$\text{Net WPM} = \frac{\text{Correct Characters} / 5}{\text{Active Elapsed Minutes}}$$
   - **Raw WPM**: Total characters typed (including mistakes) divided by 5 per minute.
   - **Accuracy**: Ratio of correct keystrokes to total input keystrokes:
     $$\text{Accuracy} = \frac{\text{Correct Keystrokes}}{\text{Total Keystrokes}} \times 100\%$$
   - Active typing duration excludes idle pauses exceeding 5 seconds.

4. **Unicode & Grapheme Cluster Integrity**:
   - Normalize all texts to Unicode NFC before comparison.
   - Use `Intl.Segmenter` (with `granularity: "grapheme"`) to guarantee combining diacritics and accented characters are processed as atomic glyph units.

5. **IME and Composition Handling**:
   - Listen to `compositionstart`, `compositionupdate`, and `compositionend`. Keystrokes are not committed to the error classifier until the IME composition session finalizes.

## Consequences

- **Positive**: Industry-standard, verifiable typing metrics; high reliability across European languages; deterministic unit testing; rich post-session analytics.
- **Negative**: Increased complexity compared to simple `<input>` string matching; requires explicit property-based tests for edge cases.
