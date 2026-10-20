import test from "node:test";
import assert from "node:assert/strict";
import { buildSentenceReview, compareMistake, describeCharacter } from "../../../apps/frontend/src/features/typing/core/review.ts";
import { createInitialTypingState, typingReducer } from "../../../apps/frontend/src/features/typing/core/reducer.ts";

const type = (state: ReturnType<typeof createInitialTypingState>, char: string) => typingReducer(state, { type: "KEY_DOWN", char, timestampMs: 1000 });
const erase = (state: ReturnType<typeof createInitialTypingState>, mode: "char" | "word" = "char") => typingReducer(state, { type: "BACKSPACE", mode, timestampMs: 1100 });

test("US QWERTY distinguishes adjacent, diagonal, and distant keys", () => {
  assert.equal(compareMistake("c", "v").label, "Nearby key");
  assert.equal(compareMistake("w", "a").label, "Nearby key");
  assert.equal(compareMistake("q", "p").label, "Farther key");
  assert.equal(compareMistake("q", "p").distance, 9);
});

test("case and same-key punctuation receive different Shift explanations", () => {
  assert.equal(compareMistake("A", "a").label, "Case mismatch");
  assert.match(compareMistake("Ä", "ä").explanation, /Caps Lock/);
  assert.equal(compareMistake("!", "1").label, "Shift mismatch");
  assert.equal(compareMistake("?", "/").distance, 0);
});

test("accents and unmapped graphemes do not get misleading key distances", () => {
  assert.equal(compareMistake("é", "e").label, "Accent mismatch");
  assert.equal(compareMistake("🙂", "🙃").label, "Different character");
  assert.equal(compareMistake("🙂", "x").distance, undefined);
});

test("whitespace comparisons and end-of-sentence errors are readable", () => {
  assert.equal(compareMistake(" ", "x").label, "Spacing mismatch");
  assert.equal(describeCharacter(" "), "Space");
  assert.equal(describeCharacter("\n"), "Newline");
  assert.equal(describeCharacter("\u00a0"), "Nonbreaking space");
  assert.equal(describeCharacter(null), "End of sentence");
});

test("a corrected error remains in the review after Backspace", () => {
  const state = type(erase(type(createInitialTypingState("A cat."), "x")), "A cat.");
  const review = buildSentenceReview(state);
  assert.equal(review.typed.join(""), "A cat.");
  assert.equal(review.mistakes.length, state.mistakeCount);
  assert.equal(review.mistakes[0].expected, "A");
  assert.equal(review.mistakes[0].typed, "x");
  assert.equal(review.mistakes[0].position, 1);
  assert.equal(review.mistakes[0].status, "Corrected");
});

test("repeated wrong attempts distinguish removed attempts from the final error", () => {
  const state = type(erase(type(createInitialTypingState("A cat."), "x")), "y cat.");
  const review = buildSentenceReview(state);
  assert.deepEqual(review.mistakes.map(mistake => mistake.status), ["Retried", "Still present"]);
  assert.deepEqual(review.mistakes.map(mistake => mistake.typed), ["x", "y"]);
});

test("word deletion preserves corrected error history", () => {
  const state = type(erase(type(createInitialTypingState("cat."), "cz"), "word"), "cat.");
  const mistake = buildSentenceReview(state).mistakes[0];
  assert.equal(mistake.expected, "a");
  assert.equal(mistake.typed, "z");
  assert.equal(mistake.status, "Corrected");
});

test("review positions count graphemes rather than UTF-16 units", () => {
  const state = type(createInitialTypingState("é🙂x."), "e\u0301🙂y.");
  const review = buildSentenceReview(state);
  assert.equal(review.mistakes.length, 1);
  assert.equal(review.mistakes[0].position, 3);
  assert.equal(review.mistakes[0].expected, "x");
});

test("overshooting a target produces an explicit extra-character comparison", () => {
  const mistake = buildSentenceReview(type(createInitialTypingState("ab"), "abc")).mistakes[0];
  assert.equal(mistake.expected, null);
  assert.equal(mistake.comparison.label, "Extra character");
});

test("restart removes earlier mistakes from the next attempt", () => {
  const state = typingReducer(type(createInitialTypingState("cat."), "x"), { type: "RESTART", timestampMs: 1200 });
  assert.deepEqual(buildSentenceReview(type(state, "cat.")).mistakes, []);
});
