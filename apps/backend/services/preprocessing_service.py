"""Service for processing raw text into sentences and extracting word frequencies."""

from collections import Counter
from typing import Any, Dict, List, Tuple

import spacy
from services.text_sanitizer import TextSanitizer


class PreprocessingService:
    """Preprocess raw text using spaCy."""

    def __init__(self) -> None:
        """Initialize the spaCy NLP pipeline."""
        self._models: Dict[str, Any] = {}

    def _get_nlp(self, language: str):
        lang_map = {
            "german": "de_core_news_sm",
            "italian": "it_core_news_sm",
            "french": "fr_core_news_sm",
            "spanish": "es_core_news_sm",
            "english": "en_core_web_sm"
        }
        model_name = lang_map.get(language.lower(), "en_core_web_sm")
        
        if model_name not in self._models:
            try:
                self._models[model_name] = spacy.load(model_name)
            except OSError:
                print(f"Failed to load {model_name}, falling back to en_core_web_sm")
                if "en_core_web_sm" not in self._models:
                    self._models["en_core_web_sm"] = spacy.load("en_core_web_sm")
                return self._models["en_core_web_sm"]
        return self._models[model_name]

    def process_text(
        self, text: str, language: str = "english", filtering_method: str = "spacy"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split text into paragraphs and sentences, and calculate word frequencies.

        Returns:
            A tuple of (paragraphs, word_frequencies).
            paragraphs is a list of {"index": int, "sentences": [{"index": int, "text": str}]}
            word_frequencies is a list of {"word": str, "count": int} sorted by frequency.
        """
        paragraphs_data = []
        word_counts = Counter()

        text = TextSanitizer.sanitize(text)

        # Split into paragraphs natively to preserve explicit line breaks
        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        nlp = self._get_nlp(language)

        for p_idx, p_text in enumerate(raw_paragraphs):
            # Process the whole paragraph with spaCy
            doc = nlp(p_text)

            sentences_data = []
            current_sentence = ""
            for sent in doc.sents:
                s_text = sent.text.strip()
                if not s_text:
                    continue
                    
                if current_sentence:
                    # Merge if starts with lowercase, is very short, or has no letters (e.g. `!«`)
                    if s_text[0].islower() or len(s_text) <= 2 or not any(c.isalpha() for c in s_text):
                        current_sentence += " " + s_text
                    else:
                        sentences_data.append({
                            "index": len(sentences_data),
                            "text": current_sentence,
                        })
                        current_sentence = s_text
                else:
                    current_sentence = s_text
                    
            if current_sentence:
                sentences_data.append({
                    "index": len(sentences_data),
                    "text": current_sentence,
                })

            paragraphs_data.append(
                {
                    "index": p_idx,
                    "sentences": sentences_data,
                }
            )

            # Count word frequencies
            for token in doc:
                if filtering_method == "llm":
                    # For LLM filtering, just collect raw alphabetic tokens
                    if not token.is_punct and not token.is_space and token.is_alpha:
                        word_counts[token.text.lower()] += 1
                else:
                    # For spacy filtering, do full POS and stop word filtering
                    if (
                        not token.is_stop
                        and not token.is_punct
                        and not token.is_space
                        and token.is_alpha
                        and token.pos_ in {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
                    ):
                        lemma = token.lemma_.lower()
                        word_counts[lemma] += 1

        if filtering_method == "llm":
            # Just return top 50 raw tokens for LLM to process further
            word_frequencies = [
                {"word": word, "count": count} for word, count in word_counts.most_common(50)
            ]
        else:
            word_frequencies = [
                {"word": word, "count": count} for word, count in word_counts.most_common()
            ]

        return paragraphs_data, word_frequencies
