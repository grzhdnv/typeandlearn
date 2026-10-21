"""Canonical handling of absent descriptive metadata from users and providers."""

from typing import Annotated

from pydantic import BeforeValidator


def normalize_optional_metadata(value: str | None) -> str | None:
    """Treat only empty values and serialized null sentinels as absent."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Metadata must be text or null")
    value = value.strip()
    return None if value.casefold() in {"", "null", "none", "undefined"} else value


OptionalMetadata = Annotated[str | None, BeforeValidator(normalize_optional_metadata)]
