"""Backend settings and environment bootstrap."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    """Strongly typed configuration values for backend services."""

    translation_prompt_file: Path = Path("apps/backend/prompts/translate_sentence.md")
    practice_prompt_file: Path = Path("apps/backend/prompts/generate_practice.md")
    # Pydantic AI format: "provider:model_name"
    model_name: str = Field(default="groq:llama-3.3-70b-versatile")
    fallback_models: list[str] = Field(
        default_factory=lambda: [
            "groq:openai/gpt-oss-120b",
            "groq:qwen/qwen3-32b",
            "groq:openai/gpt-oss-20b"
        ]
    )


settings = Settings()
