"""Database connection and session management."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

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

    # Ensure the parent directory of a file-backed SQLite database exists
    sqlite_prefix = "sqlite:///"
    if database_url.startswith(sqlite_prefix):
        sqlite_path = Path(database_url.removeprefix(sqlite_prefix))
        if sqlite_path.parent != Path("."):
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)

# SQLite-specific configuration for FastAPI's multithreaded requests
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(database_url, connect_args=connect_args, echo=False)



def run_migrations() -> None:
    """Execute Alembic migrations programmatically up to head."""
    backend_dir = Path(__file__).resolve().parents[1]
    root_dir = backend_dir.parent.parent
    alembic_ini = root_dir / "alembic.ini"
    if not alembic_ini.exists():
        alembic_ini = backend_dir / "alembic.ini"

    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")


def init_db() -> None:
    """Initialize database tables using versioned Alembic migrations."""
    run_migrations()


def get_session():
    """FastAPI dependency for obtaining a database session."""
    with Session(engine) as session:
        yield session
