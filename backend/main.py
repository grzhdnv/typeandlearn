from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/texts")
def get_texts():
    """Endpoint to retrieve all texts."""
    return {"message": "Here is all the texts data!"}


@app.get("/texts/{text_id}")
def get_text(text_id: str):
    """Endpoint to retrieve text data by ID."""
    return {"message": f"Data for text {text_id}"}


@app.post("/texts")
def create_text(text: dict):
    """Endpoint to add new text."""
    return {"message": "Text created successfully!", "text": text}
