import { segmentGraphemes } from "./unicode.ts";

export interface HintGroup { words: string[]; hint: string }
export interface HintSpan { word: string; start: number; end: number; group: HintGroup | null }

export function hintWordKey(word: string): string {
  return word.normalize("NFC").replace(/[’‘ʼ＇]/gu, "'").replace(/[‐‑]/gu, "-")
    .replace(/^\p{P}+|\p{P}+$/gu, "");
}

/** Assign by occurrence so repeated words can have different contextual meanings. */
export function buildHintSpans(text: string, hints: HintGroup[]): HintSpan[] {
  const graphemes = segmentGraphemes(text);
  const spans: HintSpan[] = [];
  let i = 0;
  while (i < graphemes.length) {
    if (/\s/u.test(graphemes[i])) { i++; continue; }
    const start = i;
    while (i < graphemes.length && !/\s/u.test(graphemes[i])) i++;
    spans.push({ word: graphemes.slice(start, i).join(""), start, end: i, group: null });
  }
  const keys = spans.map(s => hintWordKey(s.word));
  const candidates = new Map<string, HintGroup[]>();
  for (const group of hints) {
    for (const entry of group.words) {
      for (const word of entry.split(/\s+/u)) {
        const key = hintWordKey(word);
        if (!key) continue;
        const groups = candidates.get(key) ?? [];
        if (!groups.includes(group)) groups.push(group);
        candidates.set(key, groups);
        const index = spans.findIndex((s, n) => s.group === null && keys[n] === key);
        if (index >= 0) spans[index].group = group;
      }
    }
  }
  // Older saved hints sometimes listed a repeated word only once.
  for (let n = 0; n < spans.length; n++) {
    const groups = candidates.get(keys[n]);
    if (!spans[n].group && groups?.length === 1) spans[n].group = groups[0];
  }
  return spans;
}

export function hintAt(spans: HintSpan[], cursor: number): HintSpan | null {
  let current: HintSpan | null = null;
  for (const span of spans) {
    if (span.start > cursor) break;
    current = span;
  }
  return current;
}
