This is prompt for processing texts and saving them to the database in a structured format. 

LLM should clean the text in German from any content not related to the main text. 
Then it should process it to return the following structured data:
- JSON object with the following fields:
  - title: The title of the text
  - original paragraphs:
    - index: The index of the paragraph in the original text
    - sentences
      - index: The index of the sentence in the original paragraph
      - text: The original sentence text
      - translation: The English translation of the sentence
      - translation hints: 
        - original lexical item: English translation (taken from translation)
  - practice sentences based on the original text for language learners:
    - index: The index of the practice sentence
    - sentence: generated practice sentence to practice similar words, but different from the original text
    - translation: The English translation of the sentence
    - translation hints: 
      - original lexical item: English translation (taken from translation)


Here is an example:

input text title: "Der Hund im Park"
input text:
"""
Der Hund läuft im Park. Er ist sehr schnell. Das Wetter ist schön.

Einige Leute spielen Fußball. Kinder lachen und haben Spaß. Es ist ein perfekter Tag für einen Spaziergang mit dem Hund.
"""

output:

```json
{
  "title": "Der Hund im Park",
  "original_paragraphs": [
    {
      "index": 0,
      "sentences": [
        {
          "index": 0,
          "text": "Der Hund läuft im Park.",
          "translation": "The dog is running in the park.",
          "translation_hints": {
            "Der": "The",
            "Hund": "dog",
            "läuft": "is running",
            "im": "in the",
            "Park": "park",
          },},
        {
          "index": 1,
          "text": "Er ist sehr schnell.",
          "translation": "He is very fast.",
          "translation_hints": {
            "Er": "He",
            "ist": "is",
            "sehr": "very",
            "schnell": "fast",
          },},
        {
          "index": 2,
          "text": "Das Wetter ist schön.",
          "translation": "The weather is nice.",
          "translation_hints": {
            "Das": "The",
            "Wetter": "weather",
            "ist": "is",
            "schön": "nice",
          },},
      ],
    },
    {
      "index": 1,
      "sentences": [
        {
          "index": 0,
          "text": "Einige Leute spielen Fußball.",
          "translation": "Some people are playing soccer.",
          "translation_hints": {
            "Einige": "Some",
            "Leute": "people",
            "spielen": "are playing",
            "Fußball": "soccer",
          },},
        {
          "index": 1,
          "text": "Kinder lachen und haben Spaß.",
          "translation": "Children are laughing and having fun.",
          "translation_hints": {
            "Kinder": "Children",
            "lachen": "are laughing",
            "und": "and",
            "haben": "are having",
            "Spaß": "fun",
          },},
        {
          "index": 2,
          "text": "Es ist ein perfekter Tag für einen Spaziergang mit dem Hund.",
          "translation": "It is a perfect day for a walk with the dog.",
          "translation_hints": {
            "Es": "It",
            "ist": "is",
            "ein": "a",
            "perfekter": "perfect",
            "Tag": "day",
            "für": "for",
            "einen": "a",
            "Spaziergang": "walk",
            "mit": "with",
            "dem": "the",
            "Hund": "dog",
          },},
      ],
    },
  ],
  "practice_sentences": [
    {
      "index": 0,
      "sentence": "Der Junge spielt im Garten.",
      "translation": "The boy is playing in the garden.",
      "translation_hints": {
        "Der": "The",
        "Junge": "boy",
        "spielt": "is playing",
        "im": "in the",
        "Garten": "garden",
      },},
    {
      "index": 1,
      "sentence": "Die Katze schläft auf dem Sofa.",
      "translation": "The cat is sleeping on the sofa.",
      "translation_hints": {
        "Die": "The",
        "Katze": "cat",
        "schläft": "is sleeping",
        "auf": "on",
        "dem": "the",
        "Sofa": "sofa",
      },},]
}

```