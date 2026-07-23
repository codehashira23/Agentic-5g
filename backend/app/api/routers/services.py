"""SEL services router — list, describe, guarded try-it."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_container
from app.domain.services.models import ServiceStatus
from app.infrastructure.container import Container

router = APIRouter()


class ServiceView(BaseModel):
    name: str
    kind: str
    pattern: str
    owner_nf: str
    policy_tags: list[str]
    spec_ref: str
    approximates_operation: str
    idempotent: bool
    compensation: str | None
    description: str


class InvokeRequest(BaseModel):
    args: dict[str, Any] = {}


@router.get("", response_model=list[ServiceView])
async def list_services(
    kind: str | None = None,
    owner_nf: str | None = None,
    tag: str | None = None,
    c: Container = Depends(get_container),
) -> list[ServiceView]:
    descs = c.registry.list_services(kind=kind, owner_nf=owner_nf, tag=tag)
    return [ServiceView(
        name=d.name, kind=d.kind.value, pattern=d.pattern.value,
        owner_nf=d.owner_nf, policy_tags=list(d.policy_tags),
        spec_ref=d.spec_ref, approximates_operation=d.approximates_operation,
        idempotent=d.idempotent, compensation=d.compensation,
        description=d.description,
    ) for d in descs]


@router.get("/{name}", response_model=ServiceView)
async def get_service(
    name: str, c: Container = Depends(get_container)
) -> ServiceView:
    desc = c.registry.get(name)
    if not desc:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return ServiceView(
        name=desc.name, kind=desc.kind.value, pattern=desc.pattern.value,
        owner_nf=desc.owner_nf, policy_tags=list(desc.policy_tags),
        spec_ref=desc.spec_ref, approximates_operation=desc.approximates_operation,
        idempotent=desc.idempotent, compensation=desc.compensation,
        description=desc.description,
    )


@router.post("/{name}/invoke")
async def invoke_service(
    name: str,
    body: InvokeRequest,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    result = await c.invoker.invoke(
        name=name, args=body.args, caller="api",
    )
    if result.blocked:
        raise HTTPException(status_code=423, detail=result.to_agent_error())
    if result.status == ServiceStatus.REQUIRES_CONFIRMATION:
        raise HTTPException(status_code=428, detail=result.to_agent_error())
    if not result.ok:
        raise HTTPException(status_code=422, detail=result.error or "Service error")
    return {"status": "ok", "output": result.output, "latency_ms": result.latency_ms}
