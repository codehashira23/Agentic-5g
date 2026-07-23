"""Logs and events router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.infrastructure.container import Container

router = APIRouter()


@router.get("")
async def get_logs(
    correlation_id: str | None = None,
    limit: int = 100,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    from app.infrastructure.db.repos.log_repo import LogRepository
    repo = LogRepository(c.db, c.writer)
    items = await repo.get_logs(correlation_id=correlation_id, limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/events")
async def get_events(
    correlation_id: str | None = None,
    limit: int = 100,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    from app.infrastructure.db.repos.log_repo import LogRepository
    repo = LogRepository(c.db, c.writer)
    items = await repo.get_events(correlation_id=correlation_id, limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/correlation/{cid}")
async def get_correlation_narrative(
    cid: str, c: Container = Depends(get_container),
) -> dict[str, Any]:
    from app.infrastructure.db.repos.log_repo import LogRepository
    repo = LogRepository(c.db, c.writer)
    logs = await repo.get_logs(correlation_id=cid, limit=500)
    events = await repo.get_events(correlation_id=cid, limit=500)
    combined = sorted(logs + events, key=lambda r: r.get("ts", ""))
    return {"correlation_id": cid, "narrative": combined}
