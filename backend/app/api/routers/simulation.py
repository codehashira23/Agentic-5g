"""Simulation control router (09-api.md §9.6)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_container
from app.infrastructure.container import Container

router = APIRouter()


class SeedRequest(BaseModel):
    seed: int


class ScenarioRequest(BaseModel):
    name: str
    seed: int | None = None


class FaultRequest(BaseModel):
    nf_id: str
    type: str = "fail"      # fail | degrade | recover


@router.get("/status")
async def sim_status(c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.twin_service.get_status()


@router.get("/scenarios")
async def list_scenarios() -> list[str]:
    from app.application.twin_service.scenarios import SCENARIOS
    return list(SCENARIOS.keys())


@router.post("/start")
async def sim_start(c: Container = Depends(get_container)) -> dict[str, Any]:
    c.scheduler.start()
    await c.twin_service.set_status("running")
    return {"status": "running"}


@router.post("/pause")
async def sim_pause(c: Container = Depends(get_container)) -> dict[str, Any]:
    c.scheduler.pause()
    await c.twin_service.set_status("paused")
    return {"status": "paused"}


@router.post("/step")
async def sim_step(
    ticks: int = 1,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    await c.scheduler.step(n=ticks)
    return {"tick": c.scheduler.tick, "ticks_advanced": ticks}


@router.post("/reset")
async def sim_reset(
    body: ScenarioRequest | None = None,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    from app.application.twin_service.scenarios import build_twin_from_scenario
    name = body.name if body else "baseline_healthy"
    seed = body.seed if body and body.seed else 42
    new_twin = build_twin_from_scenario(name, seed=seed)
    c.twin_service._twin = new_twin
    c.twin_service._kpi_buffer.clear()
    c.scheduler.reset()
    c.rng.reseed(seed)
    await c.twin_service.set_status("stopped")
    return {"status": "reset", "scenario": name, "seed": seed}


@router.post("/seed")
async def sim_seed(body: SeedRequest, c: Container = Depends(get_container)) -> dict[str, Any]:
    c.rng.reseed(body.seed)
    return {"ok": True, "seed": body.seed}


@router.post("/fault")
async def sim_fault(body: FaultRequest, c: Container = Depends(get_container)) -> dict[str, Any]:
    from app.application.twin_service.scenarios import FaultSpec, inject_fault
    spec = FaultSpec(nf_id=body.nf_id, fault_type=body.type)
    result = inject_fault(c.twin_service._twin, spec)
    if not result.get("injected"):
        raise HTTPException(404, detail=result.get("reason", "Fault injection failed"))
    return result
