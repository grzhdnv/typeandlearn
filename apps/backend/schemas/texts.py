"""Pydantic models for text domain and API payloads."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


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


class TopWord(BaseModel):
    """A top frequency word and its dictionary translation."""
    
    word: str
    translation: Optional[str] = None


class TextData(BaseModel):
    """Canonical stored representation of one text unit."""

    id: Optional[int] = None
    title: str
    status: str
    language: str = "Unknown"
    difficulty_level: str = "Unrated"
    author: Optional[str] = None
    category: Optional[str] = None
    word_count: int = 0
    completed_sentences: int = 0
    total_sentences: int = 0
    estimated_time_minutes: int = 0
    original_paragraphs: List[Paragraph]
    practice_sentences: List[PracticeSentence]
    top_words: List[TopWord] = []


class SentenceTranslation(BaseModel):
    """LLM response schema for a single sentence translation."""

    model_config = ConfigDict(extra="allow")
    
    translation: str
    translation_hints: List[HintGroup]


class PracticeSentencesResponse(BaseModel):
    """LLM response schema for generating practice sentences."""

    model_config = ConfigDict(extra="allow")
    
    class GeneratedSentence(BaseModel):
        sentence: str
        translation: str
        translation_hints: List[HintGroup]
        
    sentences: List[GeneratedSentence]


class GeneratedMetadata(BaseModel):
    """LLM response schema for generating metadata."""
    title: str
    difficulty_level: str


class FilteredWordsResponse(BaseModel):
    """LLM response schema for filtering meaningful words."""
    
    class FilteredWord(BaseModel):
        word: str
        count: int
        
    words: List[FilteredWord]



class TextUploadRequest(BaseModel):
    """Request payload for submitting raw text content."""

    text: str
    language: str
    title: Optional[str] = None
    difficulty_level: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    filtering_method: str = "spacy"


class TextUpdateRequest(BaseModel):
    """Request payload for updating text metadata."""

    language: Optional[str] = None
    difficulty_level: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None


class RegenerateWordsRequest(BaseModel):
    """Request payload for regenerating word frequencies."""
    
    filtering_method: str = "spacy"


class ProgressUpdateRequest(BaseModel):
    """Request payload for updating reading progress."""

    sentence_index: int


class TextTitle(BaseModel):
    """Compact text identifier and title pair."""

    id: str
    title: str
    status: str
    language: str = "Unknown"
    difficulty_level: str = "Unrated"
    author: Optional[str] = None
    category: Optional[str] = None
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
