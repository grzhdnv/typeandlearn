/**
 * Pure state reducer and event processor for the typing engine.
 */

import {
  findPreviousWordBoundary,
  normalizeText,
  segmentGraphemes,
} from "./unicode.ts";
import type {
  InputEventRecord,
  TypingAction,
  TypingState,
} from "./types.ts";

/**
 * Initializes a fresh typing state for the given target text.
 */
export function createInitialTypingState(targetText: string): TypingState {
  const normalized = normalizeText(targetText);
  const targetGraphemes = segmentGraphemes(normalized);

  return {
    status: "idle",
    targetText: normalized,
    targetGraphemes,
    typedGraphemes: [],
    cursorIndex: 0,
    events: [],
    startTimeMs: null,
    lastEventTimeMs: null,
    completedTimeMs: null,
    totalKeystrokes: 0,
    correctKeystrokes: 0,
    mistakeCount: 0,
    isComposing: false,
    compositionBuffer: "",
  };
}

/**
 * Pure state reducer processing a single typing action into a new immutable state.
 */
export function typingReducer(state: TypingState, action: TypingAction): TypingState {
  switch (action.type) {
    case "KEY_DOWN": {
      if (state.status === "completed") {
        return state;
      }

      const inputGraphemes = segmentGraphemes(action.char);
      if (inputGraphemes.length === 0) {
        return state;
      }

      let currentCursor = state.cursorIndex;
      const newTyped = [...state.typedGraphemes];
      const newEvents = [...state.events];
      let newTotalKeystrokes = state.totalKeystrokes;
      let newCorrectKeystrokes = state.correctKeystrokes;
      let newMistakeCount = state.mistakeCount;

      const startTime = state.startTimeMs ?? action.timestampMs;

      for (const g of inputGraphemes) {
        const expected = state.targetGraphemes[currentCursor];
        const isCorrect = g === expected;

        newTyped.push(g);
        currentCursor++;
        newTotalKeystrokes++;

        if (isCorrect) {
          newCorrectKeystrokes++;
        } else {
          newMistakeCount++;
        }

        const eventRecord: InputEventRecord = {
          type: "insert",
          data: g,
          timestampMs: action.timestampMs,
          cursorIndex: currentCursor,
          isCorrect,
        };
        newEvents.push(eventRecord);
      }

      const isCompleted =
        currentCursor >= state.targetGraphemes.length && !state.isComposing;

      return {
        ...state,
        status: isCompleted ? "completed" : "active",
        typedGraphemes: newTyped,
        cursorIndex: currentCursor,
        events: newEvents,
        startTimeMs: startTime,
        lastEventTimeMs: action.timestampMs,
        completedTimeMs: isCompleted ? action.timestampMs : null,
        totalKeystrokes: newTotalKeystrokes,
        correctKeystrokes: newCorrectKeystrokes,
        mistakeCount: newMistakeCount,
      };
    }

    case "BACKSPACE": {
      if (state.status === "completed" || state.cursorIndex <= 0) {
        return state;
      }

      let newCursor = state.cursorIndex;
      let newTyped = state.typedGraphemes;
      const newEvents = [...state.events];

      if (action.mode === "word") {
        const boundary = findPreviousWordBoundary(state.typedGraphemes, state.cursorIndex);
        newCursor = boundary;
        newTyped = state.typedGraphemes.slice(0, boundary);
        newEvents.push({
          type: "delete_word",
          timestampMs: action.timestampMs,
          cursorIndex: newCursor,
        });
      } else {
        newCursor = state.cursorIndex - 1;
        newTyped = state.typedGraphemes.slice(0, newCursor);
        newEvents.push({
          type: "delete_char",
          timestampMs: action.timestampMs,
          cursorIndex: newCursor,
        });
      }

      return {
        ...state,
        typedGraphemes: newTyped,
        cursorIndex: newCursor,
        events: newEvents,
        lastEventTimeMs: action.timestampMs,
      };
    }

    case "COMPOSITION_START": {
      return {
        ...state,
        isComposing: true,
        compositionBuffer: "",
      };
    }

    case "COMPOSITION_UPDATE": {
      return {
        ...state,
        compositionBuffer: action.data,
      };
    }

    case "COMPOSITION_END": {
      const interimState = {
        ...state,
        isComposing: false,
        compositionBuffer: "",
      };

      if (!action.data) {
        return interimState;
      }

      // Commit the completed IME composition through standard grapheme insertion
      return typingReducer(interimState, {
        type: "KEY_DOWN",
        char: action.data,
        timestampMs: action.timestampMs,
      });
    }

    case "RESTART": {
      const reset = createInitialTypingState(state.targetText);
      return {
        ...reset,
        events: [
          {
            type: "restart",
            timestampMs: action.timestampMs,
            cursorIndex: 0,
          },
        ],
      };
    }

    case "PAUSE": {
      if (state.status === "active") {
        return {
          ...state,
          status: "paused",
          lastEventTimeMs: action.timestampMs,
        };
      }
      return state;
    }

    case "RESUME": {
      if (state.status === "paused") {
        return {
          ...state,
          status: "active",
          lastEventTimeMs: action.timestampMs,
        };
      }
      return state;
    }

    case "PASTE": {
      // Direct pasting is restricted in typing drills to protect measurement accuracy
      return state;
    }

    default:
      return state;
  }
}
