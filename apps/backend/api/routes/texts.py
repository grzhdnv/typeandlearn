"""HTTP routes for text CRUD and processing workflows with owner scoping."""

from fastapi import APIRouter, Depends, HTTPException

from app_state import text_service
from core.auth import get_current_owner_id
from schemas.texts import (
    DeleteResponse,
    ProgressUpdateRequest,
    RegenerateWordsRequest,
    TextResponse,
    TextsResponse,
    TextUpdateRequest,
    TextUploadRequest,
    TitlesResponse,
    UploadResponse,
)

router = APIRouter(prefix="/texts", tags=["texts"])


@router.get("", response_model=TextsResponse)
def get_texts(owner_id: str = Depends(get_current_owner_id)) -> TextsResponse:
    """Return all stored text entries for the authenticated owner."""
    return TextsResponse(
        message="Here is all the texts data!",
        data=text_service.get_all(owner_id),
    )


@router.get("/titles", response_model=TitlesResponse)
def get_text_titles(
    owner_id: str = Depends(get_current_owner_id),
) -> TitlesResponse:
    """Return lightweight title metadata for all texts belonging to the owner."""
    return TitlesResponse(
        message="Here are all the text titles!",
        titles=text_service.get_titles(owner_id),
    )


@router.get("/{text_id}", response_model=TextResponse)
def get_text(
    text_id: str,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Return one text entry identified by its database ID and owner."""
    return TextResponse(
        message=f"Here is the data for text {text_id}!",
        data=text_service.get_one(text_id, owner_id),
    )


@router.post("", response_model=UploadResponse)
def upload_text(
    payload: TextUploadRequest,
    owner_id: str = Depends(get_current_owner_id),
) -> UploadResponse:
    """Generate and persist structured text content from raw input."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    text_service.upload(
        text=text,
        language=payload.language,
        owner_id=owner_id,
        title=payload.title,
        difficulty_level=payload.difficulty_level,
        author=payload.author,
        category=payload.category,
        filtering_method=payload.filtering_method,
    )

    return UploadResponse(message="Text uploaded successfully", text=text)


@router.delete("/{text_id}", response_model=DeleteResponse)
def delete_text(
    text_id: str,
    owner_id: str = Depends(get_current_owner_id),
) -> DeleteResponse:
    """Delete one stored text entry by database ID and owner."""
    deleted = text_service.delete(text_id, owner_id)
    remaining = len(text_service.get_all(owner_id))
    return DeleteResponse(
        message=f"Text deleted successfully, {remaining} texts remaining",
        deleted_text=deleted,
    )


@router.patch("/{text_id}", response_model=TextResponse)
def update_text_metadata(
    text_id: str,
    payload: TextUpdateRequest,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Update text metadata (language and/or difficulty level)."""
    return TextResponse(
        message="Text metadata updated successfully!",
        data=text_service.update_metadata(text_id, payload, owner_id),
    )


@router.post("/{text_id}/progress")
def update_progress(
    text_id: str,
    payload: ProgressUpdateRequest,
    owner_id: str = Depends(get_current_owner_id),
):
    """Update the completed sentences count for a text based on the highest completed index."""
    updated = text_service.update_progress(
        text_id, payload.sentence_index, owner_id
    )
    return {
        "message": "Progress updated",
        "completed_sentences": updated.completed_sentences,
    }


@router.post("/{text_id}/reset")
def reset_progress(
    text_id: str,
    owner_id: str = Depends(get_current_owner_id),
):
    """Reset the completed sentences count for a text."""
    updated = text_service.reset_progress(text_id, owner_id)
    return {
        "message": "Progress reset",
        "completed_sentences": updated.completed_sentences,
    }


@router.post("/{text_id}/regenerate-words", response_model=TextResponse)
def regenerate_words(
    text_id: str,
    payload: RegenerateWordsRequest | None = None,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Regenerate top words and trigger background practice sentence generation."""
    method = payload.filtering_method if payload else "spacy"
    data = text_service.regenerate_words(
        text_id, owner_id, filtering_method=method
    )

    return TextResponse(
        message="Regenerating words and practice sentences...",
        data=data,
    )


@router.post("/{text_id}/retry", response_model=TextResponse)
def retry_enrichment(
    text_id: str,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Retry enrichment processing for a failed or stalled text."""
    return TextResponse(
        message="Retrying enrichment...",
        data=text_service.retry_enrichment(text_id, owner_id),
    )
