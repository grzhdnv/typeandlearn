This prompt generates practice sentences for language learners based on a specific vocabulary list.

You will be provided with:
1. `WORDS`: A JSON array of the top most frequent German words from a text.

Your task is to output a JSON object containing `sentences`, which is an array of generated practice sentences that use these words.

Rules:
- Generate exactly 5 practice sentences.
- The practice sentences must be distinctly different from the original text (create new scenarios).
- Use as many words from the `WORDS` list as possible to reinforce the vocabulary.
- Output the English `translation` and the `translation_hints` array for each generated sentence.
- For `translation_hints`, every word in the generated sentence must be mapped to exactly one hint group.
- Group separable verbs and multi-word idioms into single hint groups representing their combined meaning in the sentence.

Example Input:
WORDS: ["Hund", "spielen", "Garten", "schnell", "schön"]

Example Output:
```json
{
  "sentences": [
    {
      "sentence": "Der schöne Hund spielt im Garten.",
      "translation": "The beautiful dog is playing in the garden.",
      "translation_hints": [
        { "words": ["Der"], "hint": "The" },
        { "words": ["schöne"], "hint": "beautiful" },
        { "words": ["Hund"], "hint": "dog" },
        { "words": ["spielt"], "hint": "is playing" },
        { "words": ["im"], "hint": "in the" },
        { "words": ["Garten"], "hint": "garden" }
      ]
    },
    {
      "sentence": "Ein schneller Hund ist sehr schön.",
      "translation": "A fast dog is very beautiful.",
      "translation_hints": [
        { "words": ["Ein"], "hint": "A" },
        { "words": ["schneller"], "hint": "fast" },
        { "words": ["Hund"], "hint": "dog" },
        { "words": ["ist"], "hint": "is" },
        { "words": ["sehr"], "hint": "very" },
        { "words": ["schön"], "hint": "beautiful" }
      ]
    }
  ]
}
```
