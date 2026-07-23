"""Twin read router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.infrastructure.container import Container

router = APIRouter()


@router.get("")
async def get_twin(
    region: str | None = None,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    snap = c.twin_service.snapshot()
    states = dict(snap.nf_states)
    if region:
        states = {k: v for k, v in states.items() if v.get("region") == region}
    return {"tick": snap.tick, "health_pct": snap.health_pct, "nf_states": states}


@router.get("/nf/{nf_id}")
async def get_nf(nf_id: str, c: Container = Depends(get_container)) -> dict[str, Any]:
    snap = c.twin_service.snapshot()
    state = snap.nf_states.get(nf_id)
    if not state:
        from fastapi import HTTPException
        raise HTTPException(404, detail=f"NF '{nf_id}' not found")
    return {"id": nf_id, **state}
