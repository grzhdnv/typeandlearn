"""Application-level dependency wiring."""

from core.database import engine
from core.settings import settings
from repositories.text_repository import TextRepository
from services.llm_service import LlmService
from services.text_service import TextService


text_service = TextService(
    repository=TextRepository(engine),
    llm=LlmService(str(settings.prompt_file), settings.model_name),
)
