# To run server: fastapi dev backend/main.py

from fastapi import FastAPI, HTTPException
from backend.storage import load_data, save_data
from backend.llm_client import text_to_db

app = FastAPI()


@app.get("/texts")
def get_texts():
    """Retrieve all texts."""
    data: list[dict] = load_data()
    return {"message": "Here is all the texts data!", "data": data}


@app.get("/texts/{text_id}")
def get_text(text_id: str):
    """Retrieve text data by ID."""
    data: list[dict] = load_data()
    for text in data:
        if text["id"] == text_id:
            return {"message": "Here is the text data!", "data": text}
    raise HTTPException(status_code=404, detail="Text not found")


@app.post("/texts")
def upload_text(text: str):
    """Endpoint to add new text."""
    data = text_to_db(text).dict()  # Convert Pydantic model to dict
    # Save the new text data to the JSON file
    save_data(data)

    return {"text": text}
