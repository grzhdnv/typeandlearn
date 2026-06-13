"""Backend settings and environment bootstrap."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    """Strongly typed configuration values for backend services."""

    translation_prompt_file: Path = Path("apps/backend/prompts/translate_sentence.md")
    practice_prompt_file: Path = Path("apps/backend/prompts/generate_practice.md")
    model_name: str = Field(default="deepseek:deepseek-v4-flash")
    structured_model_name: str = Field(default="deepseek:deepseek-v4-flash")
    fallback_models: list[str] = Field(
        default_factory=lambda: []
    )


settings = Settings()
