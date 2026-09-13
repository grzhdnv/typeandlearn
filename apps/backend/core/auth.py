"""Authentication and identity resolution dependencies."""

import os
from typing import Annotated

from fastapi import Header


# Default deterministic owner ID for local development and single-user mode
DEFAULT_OWNER_ID = "owner_local_default"


def get_current_owner_id(
    x_owner_id: Annotated[str | None, Header(alias="X-Owner-Id")] = None,
) -> str:
    """Resolve the current active owner identifier.

    In local prototyping (M0-M3), allows overriding via X-Owner-Id header for
    isolation testing, defaulting to DEFAULT_OWNER_ID or env var.
    In M4, this will validate JWT bearer tokens or session cookies.
    """
    if x_owner_id and x_owner_id.strip():
        return x_owner_id.strip()
    return os.getenv("DEFAULT_OWNER_ID", DEFAULT_OWNER_ID)
