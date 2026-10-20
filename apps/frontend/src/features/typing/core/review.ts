import type { TypingState } from "./types.ts";

export type MistakeComparison = {
  label: string;
  explanation: string;
  distance?: number;
};

export type ReviewedMistake = {
  position: number;
  expected: string | null;
  typed: string;
  status: "Corrected" | "Still present" | "Retried";
  comparison: MistakeComparison;
};

export type SentenceReview = {
  expected: string[];
  typed: string[];
  mistakes: ReviewedMistake[];
};

// Approximate US QWERTY key centers, measured in key widths. Row stagger matters.
const rows = [
  { plain: "`1234567890-=", shifted: "~!@#$%^&*()_+", offset: -1.5 },
  { plain: "qwertyuiop[]\\", shifted: "QWERTYUIOP{}|", offset: 0 },
  { plain: "asdfghjkl;'", shifted: "ASDFGHJKL:\"", offset: 0.25 },
  { plain: "zxcvbnm,./", shifted: "ZXCVBNM<>?", offset: 0.75 },
];
const keys = new Map<string, { x: number; y: number }>();
rows.forEach((row, y) => {
  Array.from(row.plain).forEach((character, x) => {
    const center = { x: row.offset + x, y };
    keys.set(character, center);
    keys.set(row.shifted[x], center);
  });
});

export function compareMistake(expected: string | null, typed: string): MistakeComparison {
  if (expected === null) return { label: "Extra character", explanation: "The target sentence had already ended." };
  if (expected !== typed && expected.toLowerCase() === typed.toLowerCase()) {
    return { label: "Case mismatch", explanation: "Possible Shift or Caps Lock difference." };
  }
  const stripAccents = (value: string) => value.normalize("NFD").replace(/\p{M}/gu, "");
  if (stripAccents(expected).toLowerCase() === stripAccents(typed).toLowerCase()) {
    return { label: "Accent mismatch", explanation: "The letter or its accent differs." };
  }
  if (/\s/u.test(expected) || /\s/u.test(typed)) {
    return { label: "Spacing mismatch", explanation: "A space or line break differs from the target." };
  }
  const expectedKey = keys.get(expected);
  const typedKey = keys.get(typed);
  if (!expectedKey || !typedKey) {
    return { label: "Different character", explanation: "Key distance is unavailable for this character on US QWERTY." };
  }
  const distance = Math.hypot(expectedKey.x - typedKey.x, expectedKey.y - typedKey.y);
  if (distance === 0) {
    return { label: "Shift mismatch", explanation: "These characters share a US QWERTY key with different Shift states.", distance: 0 };
  }
  return {
    label: distance <= 1.3 ? "Nearby key" : "Farther key",
    explanation: "Approximate distance on US QWERTY; this does not establish the cause of the mistake.",
    distance: Math.round(distance * 10) / 10,
  };
}

export function describeCharacter(character: string | null): string {
  if (character === null) return "End of sentence";
  if (character === " ") return "Space";
  if (character === "\n") return "Newline";
  if (character === "\t") return "Tab";
  if (character === "\u00a0") return "Nonbreaking space";
  if (character === "\u202f") return "Narrow nonbreaking space";
  return character;
}

/** Preserve every wrong attempt, including characters subsequently backspaced. */
export function buildSentenceReview(state: TypingState): SentenceReview {
  let mistakes: { eventIndex: number; position: number; typed: string }[] = [];
  const activeInsertions = new Map<number, number>();
  state.events.forEach((event, eventIndex) => {
    if (event.type === "restart") {
      activeInsertions.clear();
      mistakes = [];
    } else if (event.type === "insert") {
      const position = event.cursorIndex - 1;
      activeInsertions.set(position, eventIndex);
      if (event.isCorrect === false && event.data !== undefined) {
        mistakes.push({ eventIndex, position, typed: event.data });
      }
    } else if (event.type === "delete_char" || event.type === "delete_word") {
      for (const position of activeInsertions.keys()) {
        if (position >= event.cursorIndex) activeInsertions.delete(position);
      }
    }
  });
  return {
    expected: [...state.targetGraphemes],
    typed: [...state.typedGraphemes],
    mistakes: mistakes.map(mistake => {
      const expected = state.targetGraphemes[mistake.position] ?? null;
      const stillPresent = activeInsertions.get(mistake.position) === mistake.eventIndex;
      return {
        position: mistake.position + 1,
        expected,
        typed: mistake.typed,
        status: stillPresent ? "Still present" : state.typedGraphemes[mistake.position] === expected ? "Corrected" : "Retried",
        comparison: compareMistake(expected, mistake.typed),
      };
    }),
  };
}
