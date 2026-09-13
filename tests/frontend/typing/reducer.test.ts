import test from "node:test";
import assert from "node:assert/strict";
import {
  createInitialTypingState,
  typingReducer,
} from "../../../apps/frontend/src/features/typing/core/reducer.ts";

test("createInitialTypingState creates expected idle baseline", () => {
  const state = createInitialTypingState("Hi");
  assert.strictEqual(state.status, "idle");
  assert.strictEqual(state.cursorIndex, 0);
  assert.deepStrictEqual(state.targetGraphemes, ["H", "i"]);
  assert.strictEqual(state.typedGraphemes.length, 0);
  assert.strictEqual(state.events.length, 0);
  assert.strictEqual(state.startTimeMs, null);
});

test("KEY_DOWN activates session and tracks correct/incorrect keystrokes", () => {
  const initial = createInitialTypingState("Cat");

  // Type correct 'C'
  const state1 = typingReducer(initial, {
    type: "KEY_DOWN",
    char: "C",
    timestampMs: 1000,
  });

  assert.strictEqual(state1.status, "active");
  assert.strictEqual(state1.cursorIndex, 1);
  assert.strictEqual(state1.startTimeMs, 1000);
  assert.strictEqual(state1.totalKeystrokes, 1);
  assert.strictEqual(state1.correctKeystrokes, 1);
  assert.strictEqual(state1.mistakeCount, 0);
  assert.strictEqual(state1.events[0].isCorrect, true);

  // Type incorrect 'o' (expected 'a')
  const state2 = typingReducer(state1, {
    type: "KEY_DOWN",
    char: "o",
    timestampMs: 1200,
  });

  assert.strictEqual(state2.cursorIndex, 2);
  assert.strictEqual(state2.totalKeystrokes, 2);
  assert.strictEqual(state2.correctKeystrokes, 1);
  assert.strictEqual(state2.mistakeCount, 1);
  assert.strictEqual(state2.events[1].isCorrect, false);
});

test("KEY_DOWN marks session completed on reaching end of target text", () => {
  const initial = createInitialTypingState("Go");

  const state1 = typingReducer(initial, {
    type: "KEY_DOWN",
    char: "G",
    timestampMs: 1000,
  });
  assert.strictEqual(state1.status, "active");

  const state2 = typingReducer(state1, {
    type: "KEY_DOWN",
    char: "o",
    timestampMs: 1200,
  });
  assert.strictEqual(state2.status, "completed");
  assert.strictEqual(state2.completedTimeMs, 1200);

  // Subsequent keystroke when completed is ignored
  const state3 = typingReducer(state2, {
    type: "KEY_DOWN",
    char: "!",
    timestampMs: 1300,
  });
  assert.strictEqual(state3.cursorIndex, 2);
  assert.strictEqual(state3.totalKeystrokes, 2);
});

test("BACKSPACE char mode pops last typed grapheme", () => {
  const initial = createInitialTypingState("Test");
  const typedState = typingReducer(initial, {
    type: "KEY_DOWN",
    char: "T",
    timestampMs: 1000,
  });

  assert.strictEqual(typedState.cursorIndex, 1);
  assert.deepStrictEqual(typedState.typedGraphemes, ["T"]);

  const backspaced = typingReducer(typedState, {
    type: "BACKSPACE",
    timestampMs: 1100,
  });

  assert.strictEqual(backspaced.cursorIndex, 0);
  assert.strictEqual(backspaced.typedGraphemes.length, 0);
  assert.strictEqual(backspaced.events[1].type, "delete_char");
});

test("BACKSPACE word mode removes up to previous word boundary", () => {
  let state = createInitialTypingState("hello world");
  for (const c of "hello w") {
    state = typingReducer(state, { type: "KEY_DOWN", char: c, timestampMs: 1000 });
  }
  assert.strictEqual(state.cursorIndex, 7); // "hello w"

  // Word backspace should remove 'w' and stop at boundary index 6 ("hello ")
  const deleted = typingReducer(state, {
    type: "BACKSPACE",
    mode: "word",
    timestampMs: 1200,
  });

  assert.strictEqual(deleted.cursorIndex, 6);
  assert.strictEqual(deleted.typedGraphemes.join(""), "hello ");
});

test("RESTART resets state while recording restart event", () => {
  let state = createInitialTypingState("Practice");
  state = typingReducer(state, { type: "KEY_DOWN", char: "P", timestampMs: 1000 });
  state = typingReducer(state, { type: "KEY_DOWN", char: "r", timestampMs: 1100 });

  const restarted = typingReducer(state, { type: "RESTART", timestampMs: 1200 });

  assert.strictEqual(restarted.status, "idle");
  assert.strictEqual(restarted.cursorIndex, 0);
  assert.strictEqual(restarted.typedGraphemes.length, 0);
  assert.strictEqual(restarted.totalKeystrokes, 0);
  assert.strictEqual(restarted.events.length, 1);
  assert.strictEqual(restarted.events[0].type, "restart");
});

test("PAUSE and RESUME transition statuses appropriately", () => {
  let state = createInitialTypingState("Pause test");
  state = typingReducer(state, { type: "KEY_DOWN", char: "P", timestampMs: 1000 });
  assert.strictEqual(state.status, "active");

  const paused = typingReducer(state, { type: "PAUSE", timestampMs: 2000 });
  assert.strictEqual(paused.status, "paused");

  const resumed = typingReducer(paused, { type: "RESUME", timestampMs: 3000 });
  assert.strictEqual(resumed.status, "active");
});
