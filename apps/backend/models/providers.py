"""Content-free reservations shared by every API and worker process."""

from typing import Optional
from sqlmodel import Field, SQLModel


class ProviderGateRecord(SQLModel, table=True):
    __tablename__ = "provider_gates"  # pyright: ignore[reportAssignmentType]
    provider: str = Field(primary_key=True)
    cooldown_until: float = 0
    tokens_reset_at: float = 0
    requests_reset_at: float = 0
    tokens_remaining: Optional[int] = None
    requests_remaining: Optional[int] = None


class ProviderCallRecord(SQLModel, table=True):
    __tablename__ = "provider_calls"  # pyright: ignore[reportAssignmentType]
    id: str = Field(primary_key=True)
    provider: str = Field(index=True)
    model: str
    owner_id: str = Field(index=True)
    task: str
    created_at: float = Field(index=True)
    status: str = "reserved"
    tokens: int
    cost_microusd: int = 0
    response_model: Optional[str] = None
    status_code: Optional[int] = None
