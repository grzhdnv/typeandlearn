/**
 * Unicode and grapheme cluster utilities for the typing engine.
 */

/**
 * Normalizes text to Unicode Normalization Form C (NFC).
 */
export function normalizeText(text: string): string {
  return text.normalize("NFC");
}

/**
 * Segments text into atomic grapheme clusters using Intl.Segmenter.
 * Handles German umlauts, French accents, Spanish inverted punctuation,
 * and combining diacritics without splitting multi-byte code points.
 */
export function segmentGraphemes(text: string): string[] {
  const normalized = normalizeText(text);

  if (typeof Intl !== "undefined" && "Segmenter" in Intl) {
    const segmenter = new Intl.Segmenter(undefined, { granularity: "grapheme" });
    const segments: string[] = [];
    for (const segment of segmenter.segment(normalized)) {
      segments.push(segment.segment);
    }
    return segments;
  }

  // Fallback for environments where Intl.Segmenter is not available
  return Array.from(normalized);
}

/**
 * Checks whether a grapheme represents whitespace.
 */
export function isWhitespaceGrapheme(grapheme: string): boolean {
  return /^\s+$/u.test(grapheme);
}

/**
 * Calculates the index of the preceding word start for word-backspace operations.
 * Traverses backward from current cursor through trailing whitespace, then through word characters.
 */
export function findPreviousWordBoundary(graphemes: string[], currentIndex: number): number {
  if (currentIndex <= 0) return 0;

  let i = currentIndex - 1;

  // Skip any whitespace immediately preceding the cursor
  while (i >= 0 && isWhitespaceGrapheme(graphemes[i])) {
    i--;
  }

  // Skip non-whitespace characters to find word start
  while (i >= 0 && !isWhitespaceGrapheme(graphemes[i])) {
    i--;
  }

  return i + 1;
}
