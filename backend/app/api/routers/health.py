from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.api.schemas.common import HealthResponse, MetaResponse
from app.infrastructure.container import Container

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health(c: Container = Depends(get_container)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        db="ok",
        bus="ok",
        llm="ready",
        sim=c.twin_service.get_status().get("status", "stopped"),
    )


@router.get("/meta", response_model=MetaResponse)
async def get_meta() -> MetaResponse:
    from datetime import datetime
    return MetaResponse(
        started_at=datetime.now(UTC).isoformat()
    )
