This prompt processes a single German sentence to generate its English translation and word-by-word translation hints.

You will be provided with:
1. `TITLE`: The title of the text the sentence comes from.
2. `CONTEXT`: The full paragraph surrounding the sentence to help you understand the tone and meaning of ambiguous words.
3. `TARGET_SENTENCE`: The specific sentence you must translate.

Your task is to output a JSON object containing:
- `translation`: The English translation of the `TARGET_SENTENCE`.
- `translation_hints`: An array of hint groups mapping the German words in the sentence to their English equivalents based on their specific contextual meaning.

Rules for `translation_hints`:
- Every word from the original German sentence should be included in exactly one hint group.
- Punctuation should be ignored.
- For separable verbs (Trennbare Verben), group both the main verb and the separated prefix into a single hint group, and map them to their combined English meaning.
- For idioms or common multi-word phrases, group the words together and map them to their combined English meaning.

Example Input:
TITLE: Der Hund im Park
CONTEXT: Einige Leute spielen Fußball. Kinder lachen und haben Spaß. Es ist ein perfekter Tag für einen Spaziergang mit dem Hund.
TARGET_SENTENCE: Kinder lachen und haben Spaß.

Example Output:
```json
{
  "translation": "Children laugh and have fun.",
  "translation_hints": [
    { "words": ["Kinder"], "hint": "Children" },
    { "words": ["lachen"], "hint": "laugh" },
    { "words": ["und"], "hint": "and" },
    { "words": ["haben", "Spaß"], "hint": "have fun" }
  ]
}
```

Example Separable Verb Input:
TITLE: Mein Morgen
CONTEXT: Ich wache früh auf. Ich stehe um 7 Uhr auf und mache mir einen Kaffee.
TARGET_SENTENCE: Ich stehe um 7 Uhr auf und mache mir einen Kaffee.

Example Separable Verb Output:
```json
{
  "translation": "I get up at 7 o'clock and make myself a coffee.",
  "translation_hints": [
    { "words": ["Ich"], "hint": "I" },
    { "words": ["stehe", "auf"], "hint": "get up" },
    { "words": ["um"], "hint": "at" },
    { "words": ["7"], "hint": "7" },
    { "words": ["Uhr"], "hint": "o'clock" },
    { "words": ["und"], "hint": "and" },
    { "words": ["mache"], "hint": "make" },
    { "words": ["mir"], "hint": "myself" },
    { "words": ["einen"], "hint": "a" },
    { "words": ["Kaffee"], "hint": "coffee" }
  ]
}
```
