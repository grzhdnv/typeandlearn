import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _get_fallback_models() -> list[str]:
    raw = os.getenv("FALLBACK_MODELS")
    if not raw:
        return ["deepseek:deepseek-flash"]
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
        default_factory=lambda: os.getenv("MODEL_NAME", "groq:openai/gpt-oss-120b")
    )
    structured_model_name: str = Field(
        default_factory=lambda: os.getenv(
            "STRUCTURED_MODEL_NAME", "groq:openai/gpt-oss-120b"
        )
    )
    fallback_models: list[str] = Field(default_factory=_get_fallback_models)
    daily_token_limit: int = Field(
        default_factory=lambda: int(os.getenv("DAILY_TOKEN_LIMIT", "50000"))
    )
    groq_rpm: int = Field(default_factory=lambda: int(os.getenv("GROQ_RPM", "24")), gt=0)
    groq_rpd: int = Field(default_factory=lambda: int(os.getenv("GROQ_RPD", "800")), gt=0)
    groq_tpm: int = Field(default_factory=lambda: int(os.getenv("GROQ_TPM", "6400")), gt=0)
    groq_tpd: int = Field(default_factory=lambda: int(os.getenv("GROQ_TPD", "160000")), gt=0)
    groq_max_wait_seconds: float = Field(default_factory=lambda: float(os.getenv("GROQ_MAX_WAIT_SECONDS", "10")), ge=0)
    openrouter_rpm: int = Field(default_factory=lambda: int(os.getenv("OPENROUTER_RPM", "16")), gt=0)
    openrouter_rpd: int = Field(default_factory=lambda: int(os.getenv("OPENROUTER_RPD", "40")), gt=0)
    openrouter_max_wait_seconds: float = Field(default_factory=lambda: float(os.getenv("OPENROUTER_MAX_WAIT_SECONDS", "10")), ge=0)
    llm_max_output_tokens: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048")), gt=0)
    llm_max_request_bytes: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_REQUEST_BYTES", "32000")), gt=0)
    deepseek_daily_usd: float = Field(default_factory=lambda: float(os.getenv("DEEPSEEK_DAILY_USD", "0.50")), ge=0)
    deepseek_monthly_usd: float = Field(default_factory=lambda: float(os.getenv("DEEPSEEK_MONTHLY_USD", "5")), ge=0)
    deepseek_input_usd_per_mtok: float = Field(default_factory=lambda: float(os.getenv("DEEPSEEK_INPUT_USD_PER_MTOK", "0.30")), ge=0)
    deepseek_cached_input_usd_per_mtok: float = Field(default_factory=lambda: float(os.getenv("DEEPSEEK_CACHED_INPUT_USD_PER_MTOK", "0.006")), ge=0)
    deepseek_output_usd_per_mtok: float = Field(default_factory=lambda: float(os.getenv("DEEPSEEK_OUTPUT_USD_PER_MTOK", "1.20")), ge=0)
    prompt_version: str = Field(
        default_factory=lambda: os.getenv("PROMPT_VERSION", "v2-multilingual")
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
    log_format: str = Field(
        default_factory=lambda: os.getenv("LOG_FORMAT", "json").lower()
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )
    environment: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development").lower()
    )
    service_name: str = Field(
        default_factory=lambda: os.getenv("SERVICE_NAME", "typeandlearn-api")
    )



settings = Settings()
