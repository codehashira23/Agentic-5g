"""
WorkflowEngine — builds and runs the 8-stage lifecycle.

Changes in D1-C001:
  - Accepts optional `bus` and `writer` so it can emit WS events and persist rows.
  - Persists a `WorkflowRow` to the DB when a workflow starts and when it ends.
  - Emits `WORKFLOW_STAGE_CHANGED` after every stage transition so the frontend
    Agent Console can update the stepper in real time.
  - Emits `WORKFLOW_COMPLETED` / `WORKFLOW_FAILED` when the lifecycle ends.

Owning docs: 13-workflow-engine.md §5, §15
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.application.workflow.routing import route_after_execute, route_after_validate
from app.application.workflow.state import WorkflowConfig, WorkflowState

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Creates WorkflowState objects and drives them through the lifecycle.

    bus and writer are optional so the engine still works in integration
    tests that don't wire the full container.
    """

    def __init__(
        self,
        orchestrator: Any,
        bus: Any | None = None,
        writer: Any | None = None,
        db: Any | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._bus = bus
        self._writer = writer
        self._db = db

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    async def start(
        self,
        goal: str,
        trigger: str = "user",
        config: WorkflowConfig | None = None,
        seed: int = 42,
        scenario: str = "baseline_healthy",
        correlation_id: str | None = None,
    ) -> WorkflowState:
        wf_id = correlation_id or f"wf_{uuid.uuid4().hex[:8]}"
        state = WorkflowState(
            id=wf_id,
            goal=goal,
            trigger=trigger,
            config=config or WorkflowConfig(),
            seed=seed,
            scenario=scenario,
        )
        logger.info("Workflow %s started: %s", wf_id, goal)

        # Persist the workflow row immediately so GET /workflows returns it
        await self._persist_workflow(state, status="running")

        state = await self._run_lifecycle(state)
        logger.info("Workflow %s finished: %s", wf_id, state.status)

        # Persist final status
        await self._persist_workflow(state, status=state.status)

        # Emit completion event
        if state.status == "completed":
            await self._emit_completed(state)
        else:
            await self._emit_failed(state)

        return state

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def _run_lifecycle(self, state: WorkflowState) -> WorkflowState:
        from app.application.workflow.nodes import (
            complete_node,
            execute_node,
            observe_node,
            plan_node,
            reason_node,
            rollback_node,
            validate_node,
        )
        orch = self._orchestrator

        # Observe → Reason → Plan
        state = await observe_node(state, orch)
        await self._emit_stage_changed(state, "observe", "reason")

        state = await reason_node(state, orch)
        await self._emit_stage_changed(state, "reason", "plan")

        state = await plan_node(state, orch)
        await self._emit_stage_changed(state, "plan", "execute")

        # Execute loop
        steps = state.plan.get("steps", [])
        state.cursor = 0
        while state.cursor < len(steps):
            state = await execute_node(state, orch)
            next_route = route_after_execute(state)
            if next_route == "validate":
                break

        await self._emit_stage_changed(state, "execute", "validate")

        # Validate
        state = await validate_node(state, orch)
        final_route = route_after_validate(state)

        if final_route == "complete":
            await self._emit_stage_changed(state, "validate", "complete")
            state = await complete_node(state, orch)
        elif final_route == "retry":
            await self._emit_stage_changed(state, "validate", "execute")
            state.cursor = max(0, state.cursor - 1)
            state = await execute_node(state, orch)
            state = await validate_node(state, orch)
            if route_after_validate(state) == "complete":
                await self._emit_stage_changed(state, "validate", "complete")
                state = await complete_node(state, orch)
            else:
                await self._emit_stage_changed(state, "validate", "rollback")
                state = await rollback_node(state, orch)
        else:
            await self._emit_stage_changed(state, "validate", "rollback")
            state = await rollback_node(state, orch)

        return state

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    async def _persist_workflow(
        self, state: WorkflowState, status: str
    ) -> None:
        """Write/update the workflows row in the DB."""
        if self._writer is None or self._db is None:
            return
        try:
            from sqlalchemy import insert

            from app.infrastructure.db.models import WorkflowRow

            now = datetime.now(UTC).isoformat()
            row_data: dict[str, Any] = {
                "id": state.id,
                "correlation_id": state.id,
                "goal": state.goal,
                "trigger": state.trigger,
                "status": status,
                "stage": state.stage,
                "attempts": state.attempts,
                "seed": state.seed,
                "scenario": state.scenario,
                "config_json": json.dumps(state.config.model_dump()),
                "error": state.error,
                "created_at": now,
                "updated_at": now,
            }
            if status in ("completed", "failed"):
                row_data["completed_at"] = now
                row_data["summary_json"] = (
                    json.dumps(state.summary) if state.summary else None
                )

            from app.infrastructure.writer.writer import WriteOp
            stmt = insert(WorkflowRow).prefix_with("OR REPLACE").values(**row_data)
            await self._writer.submit(WriteOp(stmt=stmt))

            # Also persist trace rows
            for entry in state.trace:
                from app.infrastructure.db.models import WorkflowTraceRow
                trace_data = {
                    "workflow_id": state.id,
                    "correlation_id": state.id,
                    "stage": entry.stage,
                    "agent_role": entry.agent_role,
                    "rationale": entry.rationale,
                    "structured_json": json.dumps(entry.structured, default=str),
                    "tokens_in": entry.tokens_in,
                    "tokens_out": entry.tokens_out,
                    "latency_ms": entry.latency_ms,
                    "ts": entry.ts or now,
                }
                trace_stmt = insert(WorkflowTraceRow).prefix_with("OR IGNORE").values(
                    **trace_data
                )
                await self._writer.submit(WriteOp(stmt=trace_stmt))

        except Exception as exc:
            logger.warning("Failed to persist workflow %s: %s", state.id, exc)

    # ------------------------------------------------------------------
    # WS event emitters
    # ------------------------------------------------------------------
    async def _emit_stage_changed(
        self, state: WorkflowState, from_stage: str, to_stage: str
    ) -> None:
        if self._bus is None:
            return
        try:
            from app.domain.twin.events import WorkflowStageChangedEvent
            evt = WorkflowStageChangedEvent(
                workflow_id=state.id,
                from_stage=from_stage,
                to_stage=to_stage,
                status=state.status,
                correlation_id=state.id,
            )
            await self._bus.publish(evt)
        except Exception as exc:
            logger.debug("Stage-change emit failed: %s", exc)

    async def _emit_completed(self, state: WorkflowState) -> None:
        if self._bus is None:
            return
        try:
            from app.domain.twin.events import WorkflowCompletedEvent
            await self._bus.publish(WorkflowCompletedEvent(
                workflow_id=state.id,
                goal=state.goal,
                correlation_id=state.id,
            ))
        except Exception as exc:
            logger.debug("Workflow-completed emit failed: %s", exc)

    async def _emit_failed(self, state: WorkflowState) -> None:
        if self._bus is None:
            return
        try:
            from app.domain.twin.events import WorkflowFailedEvent
            await self._bus.publish(WorkflowFailedEvent(
                workflow_id=state.id,
                error=state.error or "Workflow failed",
                correlation_id=state.id,
            ))
        except Exception as exc:
            logger.debug("Workflow-failed emit failed: %s", exc)
