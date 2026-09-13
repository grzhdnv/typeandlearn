# TypeAndLearn Typing Engine Behavior Specification

This specification defines the authoritative behavior, state transitions, input event handling, and metric calculations for the TypeAndLearn typing engine.

---

## 1. Core Principles and Invariants

1. **Deterministic Reducer**: The core typing state machine is a pure function: `(TypingState, TypingEvent) -> TypingState`. It contains no side-effects, DOM queries, or timers.
2. **Immutable Event Log**: Every user keystroke, deletion, pause, and composition action is captured as a timestamped event. All session metrics (WPM, accuracy, consistency, error points) can be deterministically replayed and verified.
3. **Unicode Grapheme Integrity**: Target texts and user inputs are normalized using Unicode Normalization Form C (NFC). Comparison occurs at the grapheme cluster level via `Intl.Segmenter(..., { granularity: "grapheme" })`, ensuring accented letters (`é`, `ñ`, `ü`) and multi-byte characters are never split into invalid codepoints.
4. **Clean-Room Autonomy**: This specification describes original behavior. No implementation details or algorithms may be copied from GPL-licensed software.

---

## 2. Input Event Model

The engine operates on a discrete sequence of events:

```typescript
export type TypingAction =
  | { type: "KEY_DOWN"; char: string; timestampMs: number }
  | { type: "BACKSPACE"; mode: "char" | "word"; timestampMs: number }
  | { type: "COMPOSITION_START"; timestampMs: number }
  | { type: "COMPOSITION_UPDATE"; data: string; timestampMs: number }
  | { type: "COMPOSITION_END"; data: string; timestampMs: number }
  | { type: "PASTE"; text: string; timestampMs: number }
  | { type: "RESTART"; timestampMs: number }
  | { type: "PAUSE"; timestampMs: number }
  | { type: "RESUME"; timestampMs: number };
```

---

## 3. Session Lifecycle State Machine

```
[IDLE] ---> (First Keystroke) ---> [ACTIVE] ---> (Target Complete) ---> [COMPLETED]
  ^                                  |   |
  |--- (RESTART Action) -------------+   +---> (Idle > 5s) ---> [PAUSED] ---> (Keystroke) ---> [ACTIVE]
```

1. **IDLE**: The target sentence is loaded and rendered. The caret rests on the first grapheme. The timer is stationary (`elapsedMs = 0`).
2. **ACTIVE**: Triggered on the first non-modifier keystroke. Timers run, and input events are recorded.
3. **PAUSED**: If no input event is received for 5.0 continuous seconds, the active session enters `PAUSED`. Time spent paused is excluded from active typing duration.
4. **COMPLETED**: Reached when all target characters have been addressed according to the completion policy. Timers stop and immutable session results are sealed.

---

## 4. Keystroke Evaluation & Error Classification

For each target grapheme $G_i$ and typed grapheme $T_i$:

- **Correct**: $T_i = G_i$. The glyph is rendered with the `.text-completed` aesthetic.
- **Incorrect (Mistake)**: $T_i \ne G_i$. The glyph is rendered with `.text-error` and flagged in the mistake log.
- **Extra Characters**: If the user continues typing within a word beyond the target word length before pressing space, extra characters are styled as overflow errors.
- **Missing Characters**: If the user skips a word boundary (by pressing space prematurely), the untyped target characters are recorded as missed.

### Deletion Rules
- **Single Backspace**: Pops the most recently typed grapheme and moves the caret backward by one grapheme position.
- **Word Backspace (`Ctrl+Backspace` / `Option+Backspace`)**: Removes all typed graphemes back to the beginning of the current word or preceding space.
- **Locked Words (Optional Policy)**: Completed words cannot be backspaced into once the subsequent word has begun, preventing artificial stat inflation (configurable per mode).

---

## 5. Metric Semantics & Calculations

All calculations derive directly from the event stream:

### 1. Active Duration ($T_{\text{active}}$)
$$T_{\text{active}} = \sum (\text{Active Intervals}) - \sum (\text{Pauses} > 5.0\text{s})$$
Expressed in minutes: $M = \frac{T_{\text{active}}}{60{,}000\text{ ms}}$.

### 2. Standard Net Words Per Minute (WPM)
A standardized word is defined as exactly 5 characters:
$$\text{Net WPM} = \frac{\text{Correct Characters} / 5}{M}$$
*If $M = 0$, Net WPM = 0.*

### 3. Raw Words Per Minute (Raw WPM)
Includes all registered keystrokes regardless of accuracy:
$$\text{Raw WPM} = \frac{\text{Total Input Keystrokes} / 5}{M}$$

### 4. Accuracy Percentage
$$\text{Accuracy} = \frac{\text{Correct Keystrokes}}{\text{Total Registered Keystrokes}} \times 100\%$$

### 5. Consistency Percentage
Computed as the coefficient of variation ($100\% - \sigma / \mu$) of rolling 1-second keystroke speeds across the active session.

---

## 6. Caret Dynamics & Focus Recovery

1. **Caret Positioning**: The visual caret coordinates are tied to the bounding rect of the active target grapheme. On newline wrap, the caret animates smoothly to the start of the next line.
2. **Focus Stealing Guard**: Clicking anywhere within the typing card focuses the hidden `<input>` element.
3. **Blur Suppression**: If the browser window loses focus, the engine immediately transitions to `PAUSED` and displays a subtle "Click or press any key to focus" overlay.

---

## 7. Keyboard Shortcuts

| Shortcut | Scope | Action |
| --- | --- | --- |
| `Ctrl+R` / `Cmd+R` | Inside Typing Canvas | Restarts current typing drill (prevents browser reload) |
| `Esc` | Anywhere | Restarts current typing drill |
| `Alt` / `Option` (Hold) | Inside Typing Canvas | Highlights current word and reveals contextual hint |
| `Alt+Cmd` / `Option+Meta` (Hold) | Inside Typing Canvas | Reveals full sentence translation |
| `[` and `]` | Practice Header | Navigates to previous / next sentence in sequence |
