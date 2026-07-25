"""Logs and events router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, text

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
    event_type: str | None = None,
    limit: int = 200,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    from app.infrastructure.db.repos.log_repo import LogRepository
    repo = LogRepository(c.db, c.writer)
    items = await repo.get_events(correlation_id=correlation_id, limit=limit)
    if event_type:
        items = [i for i in items if i.get("type", "").upper() == event_type.upper()]
    return {"items": items, "total": len(items)}


@router.get("/service-calls")
async def get_service_calls(
    correlation_id: str | None = None,
    service_name: str | None = None,
    limit: int = 100,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    """Return SEL service call records — shows what the AI agents actually did."""
    from app.infrastructure.db.models import ServiceCallRow
    async with c.db.session() as s:
        stmt = (
            select(ServiceCallRow)
            .order_by(text("ts DESC"))
            .limit(limit)
        )
        if correlation_id:
            stmt = stmt.where(ServiceCallRow.correlation_id == correlation_id)
        if service_name:
            stmt = stmt.where(ServiceCallRow.service_name.contains(service_name))
        rows = (await s.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "correlation_id": r.correlation_id,
                "service_name": r.service_name,
                "caller": r.caller,
                "status": r.status,
                "latency_ms": round(r.latency_ms or 0.0, 1),
                "ts": r.ts,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/stats")
async def get_log_stats(c: Container = Depends(get_container)) -> dict[str, Any]:
    """Return aggregate counts for the Logs stats bar."""
    from sqlalchemy import func
    from app.infrastructure.db.models import EventRow, ServiceCallRow, WorkflowRow
    async with c.db.session() as s:
        event_count = (await s.execute(select(func.count()).select_from(EventRow))).scalar() or 0
        svc_count   = (await s.execute(select(func.count()).select_from(ServiceCallRow))).scalar() or 0
        wf_count    = (await s.execute(select(func.count()).select_from(WorkflowRow))).scalar() or 0
        fault_count = (await s.execute(
            select(func.count()).select_from(EventRow)
            .where(EventRow.type == "NF_FAILED")
        )).scalar() or 0
    return {
        "event_count": event_count,
        "service_call_count": svc_count,
        "workflow_count": wf_count,
        "fault_count": fault_count,
    }


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
