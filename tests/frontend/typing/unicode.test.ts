import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeText,
  segmentGraphemes,
  isWhitespaceGrapheme,
  findPreviousWordBoundary,
} from "../../../apps/frontend/src/features/typing/core/unicode.ts";

test("Unicode Normalization - Form C (NFC)", () => {
  // e + combining acute accent (\u0301)
  const decomposed = "e\u0301";
  const composed = "é";

  assert.notStrictEqual(decomposed.length, composed.length);
  assert.strictEqual(normalizeText(decomposed), composed);
  assert.strictEqual(normalizeText(decomposed).length, 1);
});

test("Grapheme Segmentation - German Umlauts and Eszett", () => {
  const text = "Der kleine Hund läuft süß.";
  const graphemes = segmentGraphemes(text);

  assert.ok(graphemes.includes("ä"));
  assert.ok(graphemes.includes("ß"));
  assert.ok(graphemes.includes("ü"));
  assert.strictEqual(graphemes.join(""), text);
});

test("Grapheme Segmentation - French Accents and Ligatures", () => {
  const text = "L'élève français réécrit une leçon.";
  const graphemes = segmentGraphemes(text);

  assert.ok(graphemes.includes("é"));
  assert.ok(graphemes.includes("è"));
  assert.ok(graphemes.includes("ç"));
  assert.strictEqual(graphemes.join(""), text);
});

test("Grapheme Segmentation - Spanish Inverted Marks and Tilde", () => {
  const text = "¿Cómo está el niño?";
  const graphemes = segmentGraphemes(text);

  assert.strictEqual(graphemes[0], "¿");
  assert.ok(graphemes.includes("ó"));
  assert.ok(graphemes.includes("á"));
  assert.ok(graphemes.includes("ñ"));
  assert.strictEqual(graphemes.join(""), text);
});

test("isWhitespaceGrapheme correctly identifies space characters", () => {
  assert.strictEqual(isWhitespaceGrapheme(" "), true);
  assert.strictEqual(isWhitespaceGrapheme("\t"), true);
  assert.strictEqual(isWhitespaceGrapheme("\n"), true);
  assert.strictEqual(isWhitespaceGrapheme("a"), false);
  assert.strictEqual(isWhitespaceGrapheme("ü"), false);
});

test("findPreviousWordBoundary computes accurate word backtrack positions", () => {
  const sentence = "The quick brown fox";
  const graphemes = segmentGraphemes(sentence);
  // Indices:
  // "The quick brown fox"
  //  0123456789...
  // 'The ' is 0..3, 'quick' is 4..8, ' ' is 9, 'brown' is 10..14, ' ' is 15, 'fox' is 16..18.

  // Cursor at 19 (end of "fox") -> word start should be 16
  assert.strictEqual(findPreviousWordBoundary(graphemes, 19), 16);

  // Cursor at 16 (after space following "brown") -> should jump back to start of "brown" (10)
  assert.strictEqual(findPreviousWordBoundary(graphemes, 16), 10);

  // Cursor at 0 -> should remain 0
  assert.strictEqual(findPreviousWordBoundary(graphemes, 0), 0);
});
