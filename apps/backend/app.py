"""FastAPI application assembly and router registration."""

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Response, status
from sqlalchemy import text
from sqlmodel import Session

from api.routes.auth import router as auth_router
from api.routes.texts import router as texts_router
from core.database import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to bootstrap the database and resume processing."""
    # Ensure database tables exist
    init_db()

    # Informative log for offline/online state
    from app_state import llm_service
    if not llm_service.is_configured:
        print(
            "INFO: Running in offline mode: LLM service is not configured "
            "(missing DEEPSEEK_API_KEY/GROQ_API_KEY). Core library and typing practice functions are active."
        )

    # Resume any interrupted text processing
    import threading
    from app_state import text_service
    from core.auth import DEFAULT_OWNER_ID

    def resume_pending_texts():
        try:
            texts = text_service.get_all(DEFAULT_OWNER_ID)
            for t in texts:
                if t.status == "processing" and t.id is not None:
                    print(f"Resuming interrupted processing for text {t.id}...")
                    threading.Thread(
                        target=text_service.process_pending_text,
                        args=(t.id, DEFAULT_OWNER_ID),
                    ).start()
        except Exception as e:
            print(f"Failed to resume pending texts: {e}")

    resume_pending_texts()

    yield


def create_app(custom_settings: Optional[Any] = None) -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    application = FastAPI(title="TypeAndLearn API", lifespan=lifespan)

    @application.get("/healthz", tags=["health"])
    def healthz() -> Dict[str, str]:
        """Liveness probe indicating the HTTP process is running."""
        return {"status": "ok"}

    @application.get("/readyz", tags=["health"])
    def readyz(response: Response) -> Dict[str, Any]:
        """Readiness probe checking database connectivity and provider configuration."""
        from app_state import llm_service

        try:
            with Session(engine) as session:
                session.execute(text("SELECT 1"))
        except Exception as err:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "degraded",
                "database": f"unhealthy: {err}",
                "llm_configured": llm_service.is_configured,
            }

        return {
            "status": "ok",
            "database": "connected",
            "llm_configured": llm_service.is_configured,
        }

    application.include_router(texts_router)
    application.include_router(auth_router)
    return application


app = create_app()
