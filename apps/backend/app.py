"""FastAPI application assembly and router registration."""

from api.routes.texts import router as texts_router
from fastapi import FastAPI

app = FastAPI(title="TypeAndLearn API")
app.include_router(texts_router)
