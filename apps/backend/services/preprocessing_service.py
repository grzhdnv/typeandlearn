"""Service for processing raw text into sentences and extracting word frequencies."""

from collections import Counter
from typing import Any, Dict, List, Tuple

import spacy


class PreprocessingService:
    """Preprocess raw text using spaCy."""

    def __init__(self) -> None:
        """Initialize the spaCy NLP pipeline."""
        try:
            self._nlp = spacy.load("en_core_web_sm")
        except OSError as error:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' is not installed. "
                "Run: python -m spacy download en_core_web_sm"
            ) from error

    def process_text(
        self, text: str
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

        # Split into paragraphs natively to preserve explicit line breaks
        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for p_idx, p_text in enumerate(raw_paragraphs):
            # Process the whole paragraph with spaCy
            doc = self._nlp(p_text)

            sentences_data = []
            for s_idx, sent in enumerate(doc.sents):
                sentences_data.append(
                    {
                        "index": s_idx,
                        "text": sent.text.strip(),
                    }
                )

            paragraphs_data.append(
                {
                    "index": p_idx,
                    "sentences": sentences_data,
                }
            )

            # Count word frequencies: lemmatize and exclude stop words/punctuation/spaces/numbers
            for token in doc:
                if (
                    not token.is_stop
                    and not token.is_punct
                    and not token.is_space
                    and token.is_alpha
                ):
                    lemma = token.lemma_.lower()
                    word_counts[lemma] += 1

        # Convert counter to a list of dicts, sorted from most to least frequent
        word_frequencies = [
            {"word": word, "count": count} for word, count in word_counts.most_common()
        ]

        return paragraphs_data, word_frequencies
