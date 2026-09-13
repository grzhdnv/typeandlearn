import test from "node:test";
import assert from "node:assert/strict";
import {
  createInitialTypingState,
  typingReducer,
} from "../../../apps/frontend/src/features/typing/core/reducer.ts";

test("IME Composition lifecycle commits composed grapheme without premature errors", () => {
  const target = "élégant";
  const initial = createInitialTypingState(target);

  // 1. User starts IME composition (e.g. typing dead acute key)
  const compStart = typingReducer(initial, {
    type: "COMPOSITION_START",
    timestampMs: 1000,
  });

  assert.strictEqual(compStart.isComposing, true);
  assert.strictEqual(compStart.cursorIndex, 0);
  assert.strictEqual(compStart.mistakeCount, 0);

  // 2. Interim composition update
  const compUpdate = typingReducer(compStart, {
    type: "COMPOSITION_UPDATE",
    data: "´",
    timestampMs: 1050,
  });

  assert.strictEqual(compUpdate.isComposing, true);
  assert.strictEqual(compUpdate.compositionBuffer, "´");
  assert.strictEqual(compUpdate.cursorIndex, 0);
  assert.strictEqual(compUpdate.mistakeCount, 0);

  // 3. User types 'e', finalizing composition into 'é'
  const compEnd = typingReducer(compUpdate, {
    type: "COMPOSITION_END",
    data: "é",
    timestampMs: 1100,
  });

  assert.strictEqual(compEnd.isComposing, false);
  assert.strictEqual(compEnd.compositionBuffer, "");
  assert.strictEqual(compEnd.cursorIndex, 1);
  assert.strictEqual(compEnd.typedGraphemes[0], "é");
  assert.strictEqual(compEnd.correctKeystrokes, 1);
  assert.strictEqual(compEnd.mistakeCount, 0);
  assert.strictEqual(compEnd.events[0].isCorrect, true);
});

test("IME Composition with cancelled or empty payload cleanly resets buffer", () => {
  const initial = createInitialTypingState("Bonjour");

  const compStart = typingReducer(initial, {
    type: "COMPOSITION_START",
    timestampMs: 1000,
  });

  const compEnd = typingReducer(compStart, {
    type: "COMPOSITION_END",
    data: "",
    timestampMs: 1100,
  });

  assert.strictEqual(compEnd.isComposing, false);
  assert.strictEqual(compEnd.cursorIndex, 0);
  assert.strictEqual(compEnd.typedGraphemes.length, 0);
});
