"""Normalize hint spellings without inventing meanings; enforce word coverage."""

from collections import Counter
import unicodedata

from schemas.texts import HintGroup

APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "＇": "'", "‐": "-", "‑": "-"})


def word_key(value: str) -> str:
    value = unicodedata.normalize("NFC", value).translate(APOSTROPHES).strip()
    while value and unicodedata.category(value[0]).startswith("P"):
        value = value[1:]
    while value and unicodedata.category(value[-1]).startswith("P"):
        value = value[:-1]
    return value if any(c.isalnum() for c in value) else ""


def normalize_hints(source: str, hints: list[HintGroup]) -> list[HintGroup]:
    source_words = [word_key(word) for word in source.split() if word_key(word)]
    expected = Counter(source_words)
    case_forms: dict[str, set[str]] = {}
    for word in source_words:
        case_forms.setdefault(word.casefold(), set()).add(word)
    normalized = []
    observed: Counter[str] = Counter()
    for group in hints:
        if not group.hint.strip():
            raise ValueError("Every hint group must have a nonempty English meaning")
        # Phrase-valued entries are harmless if they describe actual source words.
        pieces = [p for entry in group.words for p in entry.split() if word_key(p)]
        words: list[str] = []
        i = 0
        while i < len(pieces):
            raw = unicodedata.normalize("NFC", pieces[i]).translate(APOSTROPHES)
            key = word_key(raw)
            if key not in expected:
                # Join a split contraction only inside its existing meaning group.
                end = i + 1
                while end < len(pieces) and (raw.endswith("'") or pieces[end].translate(APOSTROPHES).startswith("'")):
                    raw += pieces[end].translate(APOSTROPHES)
                    end += 1
                    if word_key(raw) in expected:
                        key = word_key(raw)
                        i = end - 1
                        break
            forms = case_forms.get(key.casefold(), set())
            if key not in expected and len(forms) == 1:
                key = next(iter(forms))
            words.append(key)
            observed[key] += 1
            i += 1
        if not words:
            raise ValueError("Every hint group must contain source words")
        normalized.append(HintGroup(words=words, hint=group.hint.strip()))
    missing = sum((expected - observed).values())
    extra = sum((observed - expected).values())
    if missing or extra:
        remaining = observed.copy()
        missing_positions = []
        for position, word in enumerate(source_words, start=1):
            if remaining[word]:
                remaining[word] -= 1
            else:
                missing_positions.append(position)
        raise ValueError(f"Hints must cover each source word occurrence exactly once (missing={missing}, extra={extra}); missing source word positions (1-based): {missing_positions}. Keep source spellings, apostrophe words, and repeated occurrences. Recompute coverage instead of copying the previous answer.")
    return normalized
