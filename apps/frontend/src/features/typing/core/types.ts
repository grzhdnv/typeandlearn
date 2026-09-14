/**
 * Core type definitions for the TypeAndLearn deterministic typing engine.
 */

export type TypingStatus = "idle" | "active" | "paused" | "completed";

export type TypingAction =
  | { type: "KEY_DOWN"; char: string; timestampMs: number }
  | { type: "BACKSPACE"; mode?: "char" | "word"; timestampMs: number }
  | { type: "COMPOSITION_START"; timestampMs: number }
  | { type: "COMPOSITION_UPDATE"; data: string; timestampMs: number }
  | { type: "COMPOSITION_END"; data: string; timestampMs: number }
  | { type: "PASTE"; text: string; timestampMs: number }
  | { type: "RESTART"; timestampMs: number }
  | { type: "PAUSE"; timestampMs: number }
  | { type: "RESUME"; timestampMs: number };

export interface InputEventRecord {
  type: "insert" | "delete_char" | "delete_word" | "composition" | "paste" | "restart";
  data?: string;
  timestampMs: number;
  cursorIndex: number;
  isCorrect?: boolean;
}

export interface TypingState {
  status: TypingStatus;
  targetText: string;
  targetGraphemes: string[];
  typedGraphemes: string[];
  cursorIndex: number;
  events: InputEventRecord[];
  startTimeMs: number | null;
  lastEventTimeMs: number | null;
  completedTimeMs: number | null;
  totalKeystrokes: number;
  correctKeystrokes: number;
  mistakeCount: number;
  isComposing: boolean;
  compositionBuffer: string;
}

export interface TypingMetrics {
  netWpm: number;
  rawWpm: number;
  accuracy: number;
  totalElapsedSeconds: number;
  activeSeconds: number;
  totalKeystrokes: number;
  correctKeystrokes: number;
  mistakeCount: number;
  completed: boolean;
}
