# ADR-0008: Clean-Room Design Policy Regarding Monkeytype (GPL-3.0)

- **Status**: Accepted
- **Date**: 2026-08-30

## Context

Monkeytype represents the gold standard for browser-based typing ergonomics, caret responsiveness, and input event handling. Monkeytype is distributed under the GNU General Public License version 3 (GPL-3.0). 

Copying, translating, or directly incorporating code from Monkeytype into TypeAndLearn would subject TypeAndLearn to the viral copyleft obligations of GPL-3.0. To retain full licensing autonomy for TypeAndLearn, a strict clean-room implementation policy is mandatory.

## Decision

1. **Strict Clean-Room Prohibition**:
   - No source code, regex patterns, CSS rules, algorithms, or test fixtures from the Monkeytype repository may be copied, pasted, or mechanically transliterated into TypeAndLearn.
   - Code contributions must be original works authored specifically for this repository.

2. **Behavioral Black-Box Benchmarking**:
   - Monkeytype may only be analyzed as an external reference for user experience expectations and standard domain behaviors (e.g., standard WPM definitions, caret smoothing feel, cursor positioning rules, backspace handling).
   - All behavior must be codified first in an original written specification ([`docs/behavior-spec.md`](../behavior-spec.md)) before implementation commences.

3. **Independent Test Authoring**:
   - All unit test vectors, keystroke fixtures, and Playwright verification scripts must be created independently from realistic user typing scenarios and synthetic test inputs.

## Consequences

- **Positive**: Complete legal clarity and freedom from GPL-3.0 copyleft contamination; architectural freedom to design idiomatic SolidJS and Python solutions.
- **Negative**: Requires authoring original typing state machines and algorithms rather than leveraging existing open source libraries.
