"""FastAPI application assembly and router registration."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.routes.texts import router as texts_router
from core.database import init_db
from core.migration import migrate_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to bootstrap the database and migrate legacy data."""
    # Ensure database tables exist
    init_db()
    # Migrate legacy db.json data if database is empty
    migrate_data()
    yield


app = FastAPI(title="TypeAndLearn API", lifespan=lifespan)
app.include_router(texts_router)
