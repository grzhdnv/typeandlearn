"""FastAPI application assembly and router registration."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.routes.texts import router as texts_router
from core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to bootstrap the database."""
    # Ensure database tables exist
    init_db()
    yield


app = FastAPI(title="TypeAndLearn API", lifespan=lifespan)
app.include_router(texts_router)
