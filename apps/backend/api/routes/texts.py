"""HTTP routes for text CRUD and processing workflows."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app_state import text_service
from schemas.texts import (
    DeleteResponse,
    TextResponse,
    TextUploadRequest,
    TextsResponse,
    TitlesResponse,
    UploadResponse,
)


router = APIRouter(prefix="/texts", tags=["texts"])


@router.get("", response_model=TextsResponse)
def get_texts() -> TextsResponse:
    """Return all stored text entries."""

    try:
        return TextsResponse(message="Here is all the texts data!", data=text_service.get_all())
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error retrieving texts: {error}")


@router.get("/titles", response_model=TitlesResponse)
def get_text_titles() -> TitlesResponse:
    """Return lightweight title metadata for all texts."""

    try:
        titles = text_service.get_titles()
        return TitlesResponse(message="Here are all the text titles!", titles=titles)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving text titles: {error}",
        )


@router.get("/{text_id}", response_model=TextResponse)
def get_text(text_id: str) -> TextResponse:
    """Return one text entry identified by its database ID."""

    try:
        data = text_service.get_one(text_id)
        return TextResponse(
            message=f"Here is the data for text {text_id}!",
            data=data,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid text ID format")
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error retrieving text: {error}")


@router.post("", response_model=UploadResponse)
def upload_text(payload: TextUploadRequest, background_tasks: BackgroundTasks) -> UploadResponse:
    """Generate and persist structured text content from raw input."""

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        record = text_service.upload(text)
        if record.id is not None:
            background_tasks.add_task(text_service.process_pending_text, record.id)
            
        return UploadResponse(message="Text uploaded successfully", text=text)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing and saving text: {error}",
        )


@router.delete("/{text_id}", response_model=DeleteResponse)
def delete_text(text_id: str) -> DeleteResponse:
    """Delete one stored text entry by database ID."""

    try:
        deleted = text_service.delete(text_id)
        remaining = len(text_service.get_all())
        return DeleteResponse(
            message=f"Text deleted successfully, {remaining} texts remaining",
            deleted_text=deleted,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid text ID format")
    except IndexError:
        raise HTTPException(status_code=404, detail="Text not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error deleting text: {error}")

