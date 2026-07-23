"""Policies router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_container
from app.infrastructure.container import Container

router = APIRouter()


@router.get("")
async def list_policies(c: Container = Depends(get_container)) -> list[dict[str, Any]]:
    from app.infrastructure.db.repos.policy_store import SqlPolicyStore
    store = SqlPolicyStore(c.db, c.writer)
    policies = await store.load_all()
    return [{"id": p.id, "name": p.name, "enabled": p.enabled,
             "severity": p.severity.value, "decision": p.decision.value,
             "message": p.message, "builtin": p.builtin} for p in policies]


@router.get("/{policy_id}")
async def get_policy(policy_id: str, c: Container = Depends(get_container)) -> dict[str, Any]:
    from app.infrastructure.db.repos.policy_store import SqlPolicyStore
    store = SqlPolicyStore(c.db, c.writer)
    p = await store.get(policy_id)
    if not p:
        raise HTTPException(404, detail=f"Policy '{policy_id}' not found")
    return {"id": p.id, "name": p.name, "enabled": p.enabled,
            "decision": p.decision.value, "message": p.message}


@router.put("/{policy_id}")
async def update_policy(
    policy_id: str,
    body: dict[str, Any],
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    from app.infrastructure.db.repos.policy_store import SqlPolicyStore
    store = SqlPolicyStore(c.db, c.writer)
    p = await store.get(policy_id)
    if not p:
        raise HTTPException(404)
    updated = p.with_enabled(body.get("enabled", p.enabled))
    await store.save(updated)
    batch = await c.writer._drain(50)
    if batch:
        await c.writer._commit(batch)
    return {"ok": True, "policy_id": policy_id}
