"""FastAPI application assembly and router registration."""

from fastapi import FastAPI

from api.routes.texts import router as texts_router


app = FastAPI(title="TypeAndLearn API")
app.include_router(texts_router)
