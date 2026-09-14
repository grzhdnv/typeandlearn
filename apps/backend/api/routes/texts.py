"""HTTP routes for text CRUD and processing workflows with owner scoping."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

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
from services import preprocessing_service

router = APIRouter(prefix="/texts", tags=["texts"])


@router.get("", response_model=TextsResponse)
def get_texts(owner_id: str = Depends(get_current_owner_id)) -> TextsResponse:
    """Return all stored text entries for the authenticated owner."""
    try:
        return TextsResponse(
            message="Here is all the texts data!",
            data=text_service.get_all(owner_id),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving texts: {error}"
        )


@router.get("/titles", response_model=TitlesResponse)
def get_text_titles(
    owner_id: str = Depends(get_current_owner_id),
) -> TitlesResponse:
    """Return lightweight title metadata for all texts belonging to the owner."""
    try:
        titles = text_service.get_titles(owner_id)
        return TitlesResponse(
            message="Here are all the text titles!", titles=titles
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving text titles: {error}",
        )


@router.get("/{text_id}", response_model=TextResponse)
def get_text(
    text_id: str,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Return one text entry identified by its database ID and owner."""
    try:
        data = text_service.get_one(text_id, owner_id)
        return TextResponse(
            message=f"Here is the data for text {text_id}!",
            data=data,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid text ID format")
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving text: {error}"
        )


@router.post("", response_model=UploadResponse)
def upload_text(
    payload: TextUploadRequest,
    background_tasks: BackgroundTasks,
    owner_id: str = Depends(get_current_owner_id),
) -> UploadResponse:
    """Generate and persist structured text content from raw input."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        record = text_service.upload(
            text=text,
            language=payload.language,
            owner_id=owner_id,
            title=payload.title,
            difficulty_level=payload.difficulty_level,
            author=payload.author,
            category=payload.category,
            filtering_method=payload.filtering_method,
        )
        if record.id is not None:
            background_tasks.add_task(
                text_service.process_pending_text, record.id, owner_id
            )

        return UploadResponse(message="Text uploaded successfully", text=text)
    except preprocessing_service.MissingLanguageModelError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing and saving text: {error}",
        )


@router.delete("/{text_id}", response_model=DeleteResponse)
def delete_text(
    text_id: str,
    owner_id: str = Depends(get_current_owner_id),
) -> DeleteResponse:
    """Delete one stored text entry by database ID and owner."""
    try:
        deleted = text_service.delete(text_id, owner_id)
        remaining = len(text_service.get_all(owner_id))
        return DeleteResponse(
            message=f"Text deleted successfully, {remaining} texts remaining",
            deleted_text=deleted,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid text ID format")
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error deleting text: {error}"
        )


@router.patch("/{text_id}", response_model=TextResponse)
def update_text_metadata(
    text_id: str,
    payload: TextUpdateRequest,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Update text metadata (language and/or difficulty level)."""
    try:
        data = text_service.update_metadata(text_id, payload, owner_id)
        return TextResponse(
            message="Text metadata updated successfully!",
            data=data,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error updating text: {error}"
        )


@router.post("/{text_id}/progress")
def update_progress(
    text_id: str,
    payload: ProgressUpdateRequest,
    owner_id: str = Depends(get_current_owner_id),
):
    """Update the completed sentences count for a text based on the highest completed index."""
    try:
        updated = text_service.update_progress(
            text_id, payload.sentence_index, owner_id
        )
        return {
            "message": "Progress updated",
            "completed_sentences": updated.completed_sentences,
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error updating progress: {error}"
        )


@router.post("/{text_id}/reset")
def reset_progress(
    text_id: str,
    owner_id: str = Depends(get_current_owner_id),
):
    """Reset the completed sentences count for a text."""
    try:
        updated = text_service.reset_progress(text_id, owner_id)
        return {
            "message": "Progress reset",
            "completed_sentences": updated.completed_sentences,
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error resetting progress: {error}"
        )


@router.post("/{text_id}/regenerate-words", response_model=TextResponse)
def regenerate_words(
    text_id: str,
    background_tasks: BackgroundTasks,
    payload: RegenerateWordsRequest | None = None,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Regenerate top words and trigger background practice sentence generation."""
    try:
        method = payload.filtering_method if payload else "spacy"
        data = text_service.regenerate_words(
            text_id, owner_id, filtering_method=method
        )
        if data.id is not None:
            background_tasks.add_task(
                text_service.process_pending_text, data.id, owner_id
            )

        return TextResponse(
            message="Regenerating words and practice sentences...",
            data=data,
        )
    except preprocessing_service.MissingLanguageModelError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error regenerating words: {error}"
        )


@router.post("/{text_id}/retry", response_model=TextResponse)
def retry_enrichment(
    text_id: str,
    background_tasks: BackgroundTasks,
    owner_id: str = Depends(get_current_owner_id),
) -> TextResponse:
    """Retry enrichment processing for a failed or stalled text."""
    try:
        data = text_service.retry_enrichment(text_id, owner_id)
        if data.id is not None:
            background_tasks.add_task(
                text_service.process_pending_text, data.id, owner_id
            )
        return TextResponse(
            message="Retrying enrichment...",
            data=data,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error retrying enrichment: {error}"
        )
