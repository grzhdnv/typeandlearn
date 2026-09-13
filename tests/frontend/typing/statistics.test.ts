import test from "node:test";
import assert from "node:assert/strict";
import {
  calculateActiveDurationMs,
  calculateNetWpm,
  calculateRawWpm,
  calculateAccuracy,
  computeSessionMetrics,
} from "../../../apps/frontend/src/features/typing/core/statistics.ts";
import type { InputEventRecord, TypingState } from "../../../apps/frontend/src/features/typing/core/types.ts";

test("calculateActiveDurationMs sums normal typing intervals", () => {
  const events: InputEventRecord[] = [
    { type: "insert", timestampMs: 1000, cursorIndex: 1 },
    { type: "insert", timestampMs: 1200, cursorIndex: 2 }, // +200ms
    { type: "insert", timestampMs: 1500, cursorIndex: 3 }, // +300ms
    { type: "insert", timestampMs: 2000, cursorIndex: 4 }, // +500ms
  ];

  const duration = calculateActiveDurationMs(events);
  assert.strictEqual(duration, 1000);
});

test("calculateActiveDurationMs discounts idle pauses exceeding threshold", () => {
  const events: InputEventRecord[] = [
    { type: "insert", timestampMs: 1000, cursorIndex: 1 },
    { type: "insert", timestampMs: 1500, cursorIndex: 2 }, // +500ms
    { type: "insert", timestampMs: 15000, cursorIndex: 3 }, // +13500ms (idle pause > 5s -> counts 1000ms)
    { type: "insert", timestampMs: 15300, cursorIndex: 4 }, // +300ms
  ];

  const duration = calculateActiveDurationMs(events);
  // 500ms + 1000ms (capped stall) + 300ms = 1800ms
  assert.strictEqual(duration, 1800);
});

test("calculateNetWpm calculates standardized (chars / 5) / minutes", () => {
  // 50 correct characters in 60,000ms (1 minute) = 10 WPM
  assert.strictEqual(calculateNetWpm(50, 60000), 10);

  // 250 correct characters in 60,000ms = 50 WPM
  assert.strictEqual(calculateNetWpm(250, 60000), 50);

  // 125 correct characters in 30,000ms (0.5 minute) = 50 WPM
  assert.strictEqual(calculateNetWpm(125, 30000), 50);

  // Zero handling
  assert.strictEqual(calculateNetWpm(0, 60000), 0);
  assert.strictEqual(calculateNetWpm(50, 0), 0);
});

test("calculateRawWpm includes total keystrokes", () => {
  // 300 total keystrokes in 60,000ms = 60 WPM
  assert.strictEqual(calculateRawWpm(300, 60000), 60);
});

test("calculateAccuracy computes ratio of correct to total", () => {
  assert.strictEqual(calculateAccuracy(95, 100), 95);
  assert.strictEqual(calculateAccuracy(100, 100), 100);
  assert.strictEqual(calculateAccuracy(0, 10), 0);
  assert.strictEqual(calculateAccuracy(0, 0), 100);
});

test("computeSessionMetrics aggregates full session state", () => {
  const state: TypingState = {
    status: "completed",
    targetText: "hello",
    targetGraphemes: ["h", "e", "l", "l", "o"],
    typedGraphemes: ["h", "e", "l", "l", "o"],
    cursorIndex: 5,
    events: [
      { type: "insert", timestampMs: 1000, cursorIndex: 1, isCorrect: true },
      { type: "insert", timestampMs: 1200, cursorIndex: 2, isCorrect: true },
      { type: "insert", timestampMs: 1400, cursorIndex: 3, isCorrect: true },
      { type: "insert", timestampMs: 1600, cursorIndex: 4, isCorrect: true },
      { type: "insert", timestampMs: 1800, cursorIndex: 5, isCorrect: true },
    ],
    startTimeMs: 1000,
    lastEventTimeMs: 1800,
    completedTimeMs: 1800,
    totalKeystrokes: 5,
    correctKeystrokes: 5,
    mistakeCount: 0,
    isComposing: false,
    compositionBuffer: "",
  };

  const metrics = computeSessionMetrics(state);
  assert.strictEqual(metrics.accuracy, 100);
  assert.strictEqual(metrics.correctKeystrokes, 5);
  assert.strictEqual(metrics.totalKeystrokes, 5);
  assert.strictEqual(metrics.mistakeCount, 0);
  assert.strictEqual(metrics.completed, true);
  assert.strictEqual(metrics.activeSeconds, 0.8);
  assert.ok(metrics.netWpm > 0);
});
