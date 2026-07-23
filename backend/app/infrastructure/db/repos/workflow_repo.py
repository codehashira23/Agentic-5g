"""Workflow repository — save/load workflows, steps, trace rows."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select

from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import WorkflowRow, WorkflowStepRow, WorkflowTraceRow
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp


class WorkflowRepository:
    def __init__(self, db: Database, writer: PersistenceWriter) -> None:
        self._db = db
        self._writer = writer

    async def save_workflow(self, workflow_id: str, data: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        data.setdefault("created_at", now)
        data["updated_at"] = now
        data["id"] = workflow_id
        data["correlation_id"] = workflow_id
        await self._writer.submit(WriteOp(
            stmt=insert(WorkflowRow).prefix_with("OR REPLACE").values(**data)
        ))

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        async with self._db.session() as s:
            row = await s.get(WorkflowRow, workflow_id)
        if row is None:
            return None
        return {
            "id": row.id, "goal": row.goal, "status": row.status,
            "stage": row.stage, "attempts": row.attempts,
            "created_at": row.created_at, "updated_at": row.updated_at,
        }

    async def list_workflows(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        async with self._db.session() as s:
            q = select(WorkflowRow).order_by(WorkflowRow.created_at.desc()).limit(limit)
            if status:
                q = q.where(WorkflowRow.status == status)
            result = await s.execute(q)
            rows = result.scalars().all()
        return [{"id": r.id, "goal": r.goal, "status": r.status} for r in rows]

    async def append_trace(self, trace_row: dict[str, Any]) -> None:
        trace_row.setdefault("ts", datetime.now(UTC).isoformat())
        await self._writer.submit(WriteOp(
            stmt=insert(WorkflowTraceRow).values(**trace_row)
        ))

    async def get_trace(self, workflow_id: str) -> list[dict[str, Any]]:
        async with self._db.session() as s:
            q = (select(WorkflowTraceRow)
                 .where(WorkflowTraceRow.workflow_id == workflow_id)
                 .order_by(WorkflowTraceRow.ts))
            result = await s.execute(q)
            rows = result.scalars().all()
        return [
            {"id": r.id, "stage": r.stage, "agent_role": r.agent_role,
             "rationale": r.rationale, "ts": r.ts}
            for r in rows
        ]

    async def save_step(self, step_row: dict[str, Any]) -> None:
        step_row.setdefault("created_at", datetime.now(UTC).isoformat())
        step_row["updated_at"] = datetime.now(UTC).isoformat()
        await self._writer.submit(WriteOp(
            stmt=insert(WorkflowStepRow).prefix_with("OR REPLACE").values(**step_row)
        ))

    async def get_steps(self, workflow_id: str) -> list[dict[str, Any]]:
        async with self._db.session() as s:
            q = (select(WorkflowStepRow)
                 .where(WorkflowStepRow.workflow_id == workflow_id)
                 .order_by(WorkflowStepRow.index))
            result = await s.execute(q)
            rows = result.scalars().all()
        return [
            {"id": r.id, "index": r.index, "service_name": r.service_name,
             "status": r.status, "attempts": r.attempts}
            for r in rows
        ]
