import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _get_fallback_models() -> list[str]:
    raw = os.getenv("FALLBACK_MODELS")
    if not raw:
        return ["deepseek:deepseek-chat"]
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(m) for m in parsed]
    except Exception:
        pass
    return [m.strip() for m in raw.split(",") if m.strip()]


class Settings(BaseModel):
    """Strongly typed configuration values for backend services."""

    translation_prompt_file: Path = Path("apps/backend/prompts/translate_sentence.md")
    practice_prompt_file: Path = Path("apps/backend/prompts/generate_practice.md")
    model_name: str = Field(
        default_factory=lambda: os.getenv("MODEL_NAME", "groq:llama-3.3-70b-versatile")
    )
    structured_model_name: str = Field(
        default_factory=lambda: os.getenv(
            "STRUCTURED_MODEL_NAME", "groq:llama-3.3-70b-versatile"
        )
    )
    fallback_models: list[str] = Field(default_factory=_get_fallback_models)
    daily_token_limit: int = Field(
        default_factory=lambda: int(os.getenv("DAILY_TOKEN_LIMIT", "50000"))
    )
    prompt_version: str = Field(
        default_factory=lambda: os.getenv("PROMPT_VERSION", "v1")
    )
    auth_mode: str = Field(
        default_factory=lambda: os.getenv("AUTH_MODE", "local").lower()
    )
    jwt_secret: str = Field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET", "typeandlearn-default-jwt-secret-dev"
        )
    )
    jwt_algorithm: str = Field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256")
    )
    jwt_audience: str | None = Field(
        default_factory=lambda: os.getenv("JWT_AUDIENCE")
    )
    jwt_issuer: str | None = Field(
        default_factory=lambda: os.getenv("JWT_ISSUER")
    )


settings = Settings()
