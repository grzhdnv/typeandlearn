/**
 * Statistical calculations for typing performance and accuracy metrics.
 */

import type { InputEventRecord, TypingMetrics, TypingState } from "./types.ts";

/**
 * Calculates active typing duration in milliseconds, excluding pauses that exceed the pause threshold.
 * Default threshold is 5,000 milliseconds (5 seconds).
 */
export function calculateActiveDurationMs(
  events: InputEventRecord[],
  maxPauseThresholdMs = 5000
): number {
  if (events.length < 2) {
    return 0;
  }

  let totalActiveMs = 0;

  for (let i = 1; i < events.length; i++) {
    const delta = events[i].timestampMs - events[i - 1].timestampMs;
    if (delta > 0) {
      if (delta <= maxPauseThresholdMs) {
        totalActiveMs += delta;
      } else {
        // Exclude the long idle pause; count only up to 1 second of transition time
        totalActiveMs += 1000;
      }
    }
  }

  return totalActiveMs;
}

/**
 * Calculates Net Words Per Minute (standard 5 characters = 1 word).
 */
export function calculateNetWpm(correctChars: number, durationMs: number): number {
  if (durationMs <= 0 || correctChars <= 0) return 0;
  const minutes = durationMs / 60000;
  const wpm = (correctChars / 5) / minutes;
  return Math.max(0, Math.round(wpm * 10) / 10);
}

/**
 * Calculates Raw Words Per Minute based on total keystrokes.
 */
export function calculateRawWpm(totalKeystrokes: number, durationMs: number): number {
  if (durationMs <= 0 || totalKeystrokes <= 0) return 0;
  const minutes = durationMs / 60000;
  const raw = (totalKeystrokes / 5) / minutes;
  return Math.max(0, Math.round(raw * 10) / 10);
}

/**
 * Calculates typing accuracy percentage.
 */
export function calculateAccuracy(correctKeystrokes: number, totalKeystrokes: number): number {
  if (totalKeystrokes <= 0) return 100;
  const pct = (correctKeystrokes / totalKeystrokes) * 100;
  return Math.min(100, Math.max(0, Math.round(pct * 10) / 10));
}

/**
 * Computes the complete metrics bundle from a typing state.
 */
export function computeSessionMetrics(state: TypingState): TypingMetrics {
  const activeMs = calculateActiveDurationMs(state.events);
  const totalElapsedMs =
    state.startTimeMs && state.lastEventTimeMs
      ? Math.max(0, state.lastEventTimeMs - state.startTimeMs)
      : 0;

  // Total correct characters currently matching the target at their position
  let correctCurrentChars = 0;
  const len = Math.min(state.typedGraphemes.length, state.targetGraphemes.length);
  for (let i = 0; i < len; i++) {
    if (state.typedGraphemes[i] === state.targetGraphemes[i]) {
      correctCurrentChars++;
    }
  }

  return {
    netWpm: calculateNetWpm(correctCurrentChars, activeMs),
    rawWpm: calculateRawWpm(state.totalKeystrokes, activeMs),
    accuracy: calculateAccuracy(state.correctKeystrokes, state.totalKeystrokes),
    totalElapsedSeconds: Math.round(totalElapsedMs / 100) / 10,
    activeSeconds: Math.round(activeMs / 100) / 10,
    totalKeystrokes: state.totalKeystrokes,
    correctKeystrokes: state.correctKeystrokes,
    mistakeCount: state.mistakeCount,
    completed: state.status === "completed",
  };
}
