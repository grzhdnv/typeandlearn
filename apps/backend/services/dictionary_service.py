"""Service for fetching dictionary translations."""

import logging
from typing import Optional
from html.parser import HTMLParser
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

class MLStripper(HTMLParser):
    """Simple HTML stripper using built-in html.parser."""
    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def get_data(self) -> str:
        return ''.join(self.text)

def strip_tags(html: str) -> str:
    """Remove HTML tags from a string."""
    s = MLStripper()
    s.feed(html)
    return s.get_data().strip()

class DictionaryService:
    """Fetch word definitions from Wiktionary."""

    def __init__(self) -> None:
        """Initialize the Dictionary Service."""
        self.base_url = "https://en.wiktionary.org/api/rest_v1/page/definition"

    def translate_word(self, word: str, source_language: str, target_language: str = "english") -> Optional[str]:
        """
        Fetch definitions for a single word using the Wiktionary REST API.
        
        Args:
            word: The word to translate.
            source_language: The source language name (e.g., "german", "spanish").
            target_language: Unused for Wiktionary since we hit the English wiktionary.
            
        Returns:
            A formatted string containing all definitions grouped by part of speech,
            or None if lookup failed.
        """
        lang_map = {
            "english": "en",
            "german": "de",
            "spanish": "es",
            "french": "fr",
            "italian": "it",
            "portuguese": "pt",
            "dutch": "nl",
            "russian": "ru"
        }
        
        source_code = lang_map.get(source_language.lower(), source_language[:2].lower())
        
        # Try fetching exact word, fallback to capitalized if not found (for German nouns)
        words_to_try = [word, word.capitalize(), word.lower()]
        
        headers = {
            "User-Agent": "TypeAndLearnApp/1.0 (https://github.com/mgrzhdnv/typeandlearn; hello@typeandlearn.com)"
        }
        
        for w in words_to_try:
            url = f"{self.base_url}/{quote(w)}"
            try:
                response = httpx.get(url, headers=headers, timeout=5.0, follow_redirects=True)
                if response.status_code == 404:
                    continue # Try next capitalization
                response.raise_for_status()
                data = response.json()
                
                # Wiktionary groups definitions by the source language code
                entries = data.get(source_code, [])
                if not entries:
                    continue # No definitions for this language code, try next capitalization
                
                lines = []
                for entry in entries:
                    pos = entry.get("partOfSpeech", "Definition")
                    lines.append(f"[{pos}]")
                    for i, d in enumerate(entry.get("definitions", []), 1):
                        clean_def = strip_tags(d.get("definition", ""))
                        lines.append(f"  {i}. {clean_def}")
                
                if lines:
                    return "\n".join(lines)
            except Exception as e:
                logger.warning(f"Failed to fetch definition for '{w}' via Wiktionary API: {e}")
            
        return None
