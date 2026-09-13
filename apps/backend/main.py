"""Backend executable entrypoint for ASGI servers and local dev."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from app import app, create_app  # noqa: F401
