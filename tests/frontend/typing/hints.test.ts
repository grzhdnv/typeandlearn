import test from "node:test";
import assert from "node:assert/strict";
import { buildHintSpans, hintAt, hintWordKey } from "../../../apps/frontend/src/features/typing/core/hints.ts";

test("hints match inverted punctuation, quotation marks, NFC and apostrophe variants", () => {
  const group = { words: ["Dónde", "l'ora", "été"], hint: "meaning" };
  const spans = buildHintSpans("¿Dónde «l’ora» e\u0301té?", [group]);
  assert.ok(spans.every(s => s.group === group));
  assert.equal(hintWordKey("don’t"), "don't");
});

test("same-spelled occurrences retain different hints", () => {
  const groups = [{ words: ["Bank"], hint: "bench" }, { words: ["Bank"], hint: "bank" }];
  const spans = buildHintSpans("Bank, Bank.", groups);
  assert.equal(hintAt(spans, 0)?.group?.hint, "bench");
  assert.equal(hintAt(spans, 6)?.group?.hint, "bank");
  assert.notEqual(spans[0].group, spans[1].group);
});

test("noncontiguous verb hints and legacy phrase entries remain usable", () => {
  const verb = { words: ["stehe", "auf"], hint: "get up" };
  const spans = buildHintSpans("Ich stehe früh auf.", [verb]);
  assert.equal(spans[1].group, verb);
  assert.equal(spans[3].group, verb);
  const phrase = { words: ["de la"], hint: "of the" };
  assert.ok(buildHintSpans("de la", [phrase]).every(s => s.group === phrase));
});

test("cursor offsets use graphemes and old repeated-word hints can be reused", () => {
  const group = { words: ["été"], hint: "summer" };
  const spans = buildHintSpans("😊 e\u0301té été.", [group]);
  assert.equal(hintAt(spans, 2)?.word, "été");
  assert.equal(hintAt(spans, 6)?.group, group);
  assert.equal(hintAt([], 0), null);
});
