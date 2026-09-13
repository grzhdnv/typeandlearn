"""Application-level dependency wiring."""

from core.database import engine
from core.settings import settings
from repositories.cache_repository import CacheRepository
from repositories.job_repository import JobRepository
from repositories.text_repository import TextRepository
from services.dictionary_service import DictionaryService
from services.llm_service import LlmService
from services.preprocessing_service import PreprocessingService
from services.text_service import TextService

cache_repository = CacheRepository(engine)
job_repository = JobRepository(engine)

llm_service = LlmService(
    str(settings.translation_prompt_file),
    str(settings.practice_prompt_file),
    settings.model_name,
    settings.structured_model_name,
    settings.fallback_models,
)

text_service = TextService(
    repository=TextRepository(engine),
    llm=llm_service,
    preprocessing=PreprocessingService(),
    dictionary=DictionaryService(),
    job_repository=job_repository,
    cache_repository=cache_repository,
    daily_token_limit=settings.daily_token_limit,
    prompt_version=settings.prompt_version,
)
