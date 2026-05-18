"""Backend settings and environment bootstrap."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    """Strongly typed configuration values for backend services."""

    data_file: Path = Path("apps/backend/data/db.json")
    prompt_file: Path = Path("apps/backend/prompts/text_to_db.md")
    model_name: str = "gemini-3-flash-preview"


settings = Settings()
