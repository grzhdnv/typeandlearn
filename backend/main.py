# To run server: fastapi dev backend/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.storage import load_data, save_data
from backend.llm_client import text_to_db

app = FastAPI()


class TextUploadRequest(BaseModel):
    text: str


@app.get("/texts")
def get_texts():
    """Retrieve all texts data."""
    try:
        data: list[dict] = load_data()
        return {"message": "Here is all the texts data!", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving texts: {str(e)}")


@app.get("/texts/titles")
def get_text_titles():
    """Retrieve all text titles with access IDs.
    Can be used to quickly look up available texts without loading the full data."""
    try:
        data: list[dict] = load_data()
        titles = [
            {"id": f"{i:02d}", "title": text["title"]} for i, text in enumerate(data)
        ]
        return {"message": "Here are all the text titles!", "titles": titles}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving text titles: {str(e)}"
        )


@app.get("/texts/{text_id}")
def get_text(text_id: str):
    """Retrieve text data by its index in the data."""
    try:
        data: list[dict] = load_data()
        index = int(text_id)
        if 0 <= index < len(data):
            return {
                "message": "Here is the data for text {id}!".format(id=text_id),
                "data": data[index],
            }
        else:
            raise HTTPException(status_code=404, detail="Text not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid text ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving text: {str(e)}")


@app.post("/texts")
def upload_text(payload: TextUploadRequest):
    """Endpoint to add new text.
    This will process the text with the LLM and save the structured data to the JSON file.
    Note: Takes time to process due to LLM generation, frontend needs to handle loading state.

    Expects JSON request body in the form: {"text": "content"}.
    """

    text = payload.text

    # Validate input
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Process text with LLM
        new_entry = text_to_db(text).dict()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing text with LLM: {str(e)}"
        )

    try:
        # Load existing data and append the new entry
        all_data: list[dict] = load_data()
        all_data.append(new_entry)
        # Save all data to the JSON file
        save_data(all_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving text to database: {str(e)}"
        )

    return {"message": "Text uploaded successfully", "text": text}


@app.delete("/texts/{text_id}")
def delete_text(text_id: str):
    """Endpoint to delete a text by index in the data."""
    try:
        data: list[dict] = load_data()
        index = int(text_id)
        if 0 <= index < len(data):
            deleted_text = data.pop(index)
            save_data(data)
            return {
                "message": "Text deleted successfully, {n} texts remaining".format(
                    n=len(data)
                ),
                "deleted_text": deleted_text,
            }
        else:
            raise HTTPException(status_code=404, detail="Text not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid text ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting text: {str(e)}")
