"""FastAPI application assembly and router registration."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.routes.texts import router as texts_router
from core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to bootstrap the database and resume processing."""
    # Ensure database tables exist
    init_db()
    
    # Resume any interrupted text processing
    from app_state import text_service
    import threading
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


app = FastAPI(title="TypeAndLearn API", lifespan=lifespan)
app.include_router(texts_router)
