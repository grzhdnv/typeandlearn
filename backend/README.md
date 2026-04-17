# Backend for TypeAndLearn

This backend is built using FastAPI and serves as the API layer for the TypeAndLearn application. It provides endpoints for managing learning items, which are stored in a JSON file. The backend also integrates with a language model (LLM) to generate learning content based on user input.

## Running the Backend Server

To run the backend server, navigate to the root directory of the project and use the following command:

```bash
fastapi dev backend/main.py
```

To update python dependencies, use:

```bash
uv sync
```

Rebuild clean env: 

```bash
rm -rf .venv && uv sync
```

## Structure

- `main.py`: The main entry point of the backend, defining the API endpoints and their logic.
- `storage.py`: Contains functions for loading and saving data to a JSON file.
- `llm_client.py`: Contains the client code for interacting with the language model (LLM) API.
- `data/db.json`: The JSON file for data storage (created automatically when saving data).
- `prompts/text_to_db.md`: A prompt for complete processing of user input into a format suitable for storage in the database.

## Endpoints

- `GET /texts`: Return all stored texts data.
- `GET /texts/titles`: Return only text titles with IDs (indices) for quick listing.
- `GET /texts/{text_id}`: Return data for one text by numeric ID (index).
- `POST /texts`: Process input text with the LLM and save it to the database.
- `DELETE /texts/{text_id}`: Delete one text by numeric ID (index).
