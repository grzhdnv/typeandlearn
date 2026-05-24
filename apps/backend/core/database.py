"""Database connection and session management."""

import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session

# Get database URL from env, or default to local SQLite database file
database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Resolve absolute path to apps/backend/data/db.sqlite
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "db.sqlite"
    database_url = f"sqlite:///{db_path}"
else:
    # Replace legacy postgres:// prefix (often set by Heroku/Render) with postgresql+psycopg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# SQLite-specific configuration for FastAPI's multithreaded requests
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(database_url, connect_args=connect_args, echo=False)


def init_db() -> None:
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency for obtaining a database session."""
    with Session(engine) as session:
        yield session
