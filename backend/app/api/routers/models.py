"""Model Manager router (AIMLE model lifecycle)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_container
from app.infrastructure.container import Container

router = APIRouter()


class RegisterModelRequest(BaseModel):
    name: str
    version: str = "1.0"
    metrics: dict[str, Any] = {}


class DeployModelRequest(BaseModel):
    target: str


@router.get("")
async def list_models(c: Container = Depends(get_container)) -> list[dict[str, Any]]:
    snap = c.twin_service.snapshot()
    # Collect model info from edge + nwdaf NFs
    models = []
    for nf_id, state in snap.nf_states.items():
        if state.get("type") in ("Edge", "NWDAF"):
            nf = c.twin_service._twin.get_nf(nf_id)
            if nf and hasattr(nf, "_hosted_models"):
                for mid, mdata in nf._hosted_models.items():
                    models.append({"id": mid, "target": nf_id, **mdata})
            if nf and hasattr(nf, "_model_instances"):
                for mid, mdata in nf._model_instances.items():
                    models.append({"id": mid, "target": nf_id, **mdata})
    return models


@router.post("", status_code=201)
async def register_model(
    body: RegisterModelRequest, c: Container = Depends(get_container),
) -> dict[str, Any]:
    import uuid
    model_id = f"model_{uuid.uuid4().hex[:8]}"
    return {"model_id": model_id, "name": body.name,
            "version": body.version, "state": "registered"}


@router.post("/{model_id}/deploy")
async def deploy_model(
    model_id: str,
    body: DeployModelRequest,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    result = await c.invoker.invoke(
        "aimle.model.deploy",
        {"model_id": model_id, "target": body.target},
        caller="api",
    )
    if not result.ok:
        raise HTTPException(422, detail=result.error or "Deploy failed")
    return {"model_id": model_id, "target": body.target, "state": "deployed"}


@router.post("/{model_id}/retire")
async def retire_model(
    model_id: str,
    target: str,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    result = await c.invoker.invoke(
        "aimle.model.retire",
        {"model_id": model_id, "target": target},
        caller="api",
    )
    return {"model_id": model_id, "retired": result.ok}
