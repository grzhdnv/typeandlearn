"""Utility for sanitizing raw text and HTML before NLP processing."""

import re
from html.parser import HTMLParser


class _TagStripper(HTMLParser):
    """Collect text nodes while dropping markup and script/style contents."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


class TextSanitizer:
    """Pre-process text to remove artifacts, HTML, and weird whitespace."""

    @staticmethod
    def sanitize(text: str) -> str:
        """Fully sanitize the input text."""
        if not text:
            return ""

        # 1. Strip HTML tags safely
        if "<" in text and ">" in text:
            stripper = _TagStripper()
            stripper.feed(text)
            stripper.close()
            text = " ".join(stripper.parts)

        # 2. Remove bracketed or parenthesized page numbers (e.g., [715] or (S. 12))
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\(\s*[sS]\.\s*\d+\s*\)', '', text)

        # 3. Normalize typography (replace guillemets with standard double quotes)
        text = text.replace('»', '"').replace('«', '"').replace('„', '"').replace('“', '"')

        # 4. Normalize whitespace
        # We want to keep paragraph boundaries (\n\n) but remove single newlines.
        # So we first split by double newlines, clean up each paragraph, and rejoin.
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        normalized_paragraphs = []
        for p in paragraphs:
            # Replace single newlines with spaces
            p_clean = p.replace('\n', ' ').replace('\r', ' ')
            # Collapse multiple spaces into one
            p_clean = re.sub(r'\s+', ' ', p_clean).strip()
            if p_clean:
                normalized_paragraphs.append(p_clean)

        return "\n\n".join(normalized_paragraphs)
