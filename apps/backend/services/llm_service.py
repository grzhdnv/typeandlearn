"""Service for generating structured text data via an LLM provider."""

import os

from google import genai
from pydantic import ValidationError
from schemas.texts import TextData


class LlmService:
    """Translate raw text into validated domain models using LLM output."""

    def __init__(self, prompt_path: str, model_name: str) -> None:
        """Configure prompt source and model identity."""

        self._prompt_path = prompt_path
        self._model_name = model_name

    def text_to_db(self, input_text: str) -> TextData:
        """Generate and validate one `TextData` object from input text."""

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        prompt = self._load_prompt()
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=self._model_name,
            contents=[prompt, input_text],
        )
        if response is None or response.text is None:
            raise RuntimeError("Empty response from LLM")

        jsonified = response.text[
            response.text.find("{") : response.text.rfind("}") + 1
        ]
        try:
            return TextData.model_validate_json(jsonified)
        except ValidationError as error:
            raise RuntimeError(f"Invalid LLM response shape: {error}") from error

    def _load_prompt(self) -> str:
        """Read the prompt template from disk."""

        with open(self._prompt_path, "r", encoding="utf-8") as file:
            return file.read()
