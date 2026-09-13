"""Persistence adapters."""

from repositories.job_repository import JobRepository
from repositories.text_repository import TextRepository

__all__ = ["JobRepository", "TextRepository"]
