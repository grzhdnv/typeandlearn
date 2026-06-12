"""Pydantic models for text domain and API payloads."""

from typing import List, Optional

from pydantic import BaseModel


class HintGroup(BaseModel):
    """A group of words and their combined translation hint."""

    words: List[str]
    hint: str


class Sentence(BaseModel):
    """A sentence in the source text with translation metadata."""

    index: int
    text: str
    translation: str
    translation_hints: List[HintGroup]


class Paragraph(BaseModel):
    """A paragraph composed of source sentences."""

    index: int
    sentences: List[Sentence]


class PracticeSentence(BaseModel):
    """A generated practice sentence and its translation metadata."""

    index: int
    sentence: str
    translation: str
    translation_hints: List[HintGroup]


class TextData(BaseModel):
    """Canonical stored representation of one text unit."""

    id: Optional[int] = None
    title: str
    status: str
    language: str = "Unknown"
    difficulty_level: str = "Unrated"
    word_count: int = 0
    completed_sentences: int = 0
    total_sentences: int = 0
    estimated_time_minutes: int = 0
    original_paragraphs: List[Paragraph]
    practice_sentences: List[PracticeSentence]


class SentenceTranslation(BaseModel):
    """LLM response schema for a single sentence translation."""
    
    translation: str
    translation_hints: List[HintGroup]


class PracticeSentencesResponse(BaseModel):
    """LLM response schema for generating practice sentences."""
    
    class GeneratedSentence(BaseModel):
        sentence: str
        translation: str
        translation_hints: List[HintGroup]
        
    sentences: List[GeneratedSentence]


class GeneratedMetadata(BaseModel):
    """LLM response schema for generating metadata."""
    title: str
    difficulty_level: str



class TextUploadRequest(BaseModel):
    """Request payload for submitting raw text content."""

    text: str
    language: str
    title: Optional[str] = None
    difficulty_level: Optional[str] = None


class TextUpdateRequest(BaseModel):
    """Request payload for updating text metadata."""

    language: Optional[str] = None
    difficulty_level: Optional[str] = None


class TextTitle(BaseModel):
    """Compact text identifier and title pair."""

    id: str
    title: str
    status: str
    language: str = "Unknown"
    difficulty_level: str = "Unrated"
    word_count: int = 0
    completed_sentences: int = 0
    total_sentences: int = 0
    estimated_time_minutes: int = 0


class TextsResponse(BaseModel):
    """API response containing all text entries."""

    message: str
    data: List[TextData]


class TitlesResponse(BaseModel):
    """API response containing text titles only."""

    message: str
    titles: List[TextTitle]


class TextResponse(BaseModel):
    """API response containing one text entry."""

    message: str
    data: TextData


class UploadResponse(BaseModel):
    """API response for successful text upload requests."""

    message: str
    text: str


class DeleteResponse(BaseModel):
    """API response for successful text deletion requests."""

    message: str
    deleted_text: TextData
