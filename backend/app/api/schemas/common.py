"""
Common request/response schemas used across all API routers.
Owning docs: 09-api.md §4-§5, §11
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    """Standard paginated list response."""
    items: list[T]
    page: int = 1
    page_size: int = 20
    total: int = 0


class ErrorEnvelope(BaseModel):
    """
    RFC 7807-inspired error envelope (09-api.md §5).
    Returned for all non-2xx responses.
    """
    type: str = "https://agent5g.local/errors/generic"
    title: str
    status: int
    detail: str = ""
    correlation_id: str | None = None
    errors: list[dict[str, str]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    db: str = "ok"
    bus: str = "ok"
    llm: str = "ready"
    sim: str = "stopped"


class MetaResponse(BaseModel):
    version: str = "0.1.0"
    api: str = "v1"
    schema_version: str = "1"
    started_at: str = ""


class OkResponse(BaseModel):
    ok: bool = True
    message: str = ""
