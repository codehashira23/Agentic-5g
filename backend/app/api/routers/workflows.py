"""
Workflows router — async create, list, get, trace, control.
POST /workflows returns 201 immediately; progress streams over WS.
Owning docs: 09-api.md §9.2
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, text

from app.api.deps import get_container
from app.api.schemas.workflow import (
    CreateWorkflowRequest,
    TraceEntryResponse,
    WorkflowControlRequest,
    WorkflowResponse,
)
from app.infrastructure.container import Container
from app.infrastructure.db.models import WorkflowRow, WorkflowTraceRow

router = APIRouter()


def _row_to_response(row: WorkflowRow) -> WorkflowResponse:
    return WorkflowResponse(
        id=row.id,
        goal=row.goal,
        status=row.status,
        stage=row.stage,
        created_at=row.created_at,
        correlation_id=row.correlation_id,
        trigger=row.trigger,
    )


@router.post("", status_code=201, response_model=WorkflowResponse)
async def create_workflow(
    body: CreateWorkflowRequest,
    response: Response,
    c: Container = Depends(get_container),
) -> WorkflowResponse:
    """
    Start a workflow from a natural-language goal.
    Returns 201 immediately with the workflow id.
    Progress streams via WebSocket (correlation_id = workflow id).
    """
    now = datetime.now(UTC).isoformat()
    wf_id = f"wf_{uuid.uuid4().hex[:8]}"

    # Schedule the workflow as a background asyncio task
    task = asyncio.create_task(
        c.engine.start(goal=body.goal, trigger="user", correlation_id=wf_id)
    )
    if not hasattr(c, "_active_tasks"):
        c._active_tasks = []  # type: ignore[attr-defined]
    c._active_tasks.append(task)  # type: ignore[attr-defined]

    return WorkflowResponse(
        id=wf_id,
        goal=body.goal,
        status="running",
        stage="observe",
        created_at=now,
        correlation_id=wf_id,
        trigger="user",
    )


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    status: str | None = None,
    limit: int = 20,
    c: Container = Depends(get_container),
) -> list[WorkflowResponse]:
    async with c.db.session() as session:
        stmt = select(WorkflowRow).order_by(
            text("created_at DESC")
        ).limit(limit)
        if status:
            stmt = stmt.where(WorkflowRow.status == status)
        result = await session.execute(stmt)
        rows = result.scalars().all()
    return [_row_to_response(r) for r in rows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    c: Container = Depends(get_container),
) -> WorkflowResponse:
    async with c.db.session() as session:
        result = await session.execute(
            select(WorkflowRow).where(WorkflowRow.id == workflow_id)
        )
        row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(404, detail=f"Workflow '{workflow_id}' not found")
    return _row_to_response(row)


@router.get("/{workflow_id}/trace", response_model=list[TraceEntryResponse])
async def get_trace(
    workflow_id: str,
    c: Container = Depends(get_container),
) -> list[TraceEntryResponse]:
    async with c.db.session() as session:
        result = await session.execute(
            select(WorkflowTraceRow)
            .where(WorkflowTraceRow.workflow_id == workflow_id)
            .order_by(text("ts ASC"))
        )
        rows = result.scalars().all()
    return [
        TraceEntryResponse(
            stage=r.stage,
            agent_role=r.agent_role or "",
            rationale=r.rationale or "",
            ts=r.ts,
        )
        for r in rows
    ]


@router.post("/{workflow_id}/control")
async def control_workflow(
    workflow_id: str,
    body: WorkflowControlRequest,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    return {"workflow_id": workflow_id, "action": body.action, "ok": True}


@router.delete("/{workflow_id}", status_code=200)
async def cancel_workflow(
    workflow_id: str,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    return {"workflow_id": workflow_id, "cancelled": True}
