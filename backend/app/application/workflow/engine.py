"""
WorkflowEngine — builds and runs the 8-stage LangGraph StateGraph.

Owning docs: 13-workflow-engine.md §5, §15
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.application.workflow.routing import route_after_execute, route_after_validate
from app.application.workflow.state import WorkflowConfig, WorkflowState

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Creates WorkflowState objects and drives them through the lifecycle
    using the AgentOrchestrator.

    For Phase 5 (Gate G5) we run the lifecycle sequentially (no real
    LangGraph graph yet — that requires the checkpointer wiring in C097).
    The graph is wired in build_graph() which is called by the orchestrator.
    """

    def __init__(self, orchestrator: Any) -> None:
        self._orchestrator = orchestrator

    async def start(
        self,
        goal: str,
        trigger: str = "user",
        config: WorkflowConfig | None = None,
        seed: int = 42,
        scenario: str = "baseline_healthy",
        correlation_id: str | None = None,
    ) -> WorkflowState:
        """
        Create a WorkflowState and run the full lifecycle.
        Returns the final state (completed or failed).
        """
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
        state = await self._run_lifecycle(state)
        logger.info("Workflow %s finished: %s", wf_id, state.status)
        return state

    async def _run_lifecycle(self, state: WorkflowState) -> WorkflowState:
        """Sequential lifecycle execution (LangGraph graph wired in C097)."""
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
        state = await reason_node(state, orch)
        state = await plan_node(state, orch)

        # Execute loop
        steps = state.plan.get("steps", [])
        state.cursor = 0
        while state.cursor < len(steps):
            state = await execute_node(state, orch)
            next_route = route_after_execute(state)
            if next_route == "validate":
                break
            # next_route == "execute" → cursor already advanced in routing

        # Validate
        state = await validate_node(state, orch)
        final_route = route_after_validate(state)

        if final_route == "complete":
            state = await complete_node(state, orch)
        elif final_route == "retry":
            # Simple single retry for Phase 5
            state.cursor = max(0, state.cursor - 1)
            state = await execute_node(state, orch)
            state = await validate_node(state, orch)
            if route_after_validate(state) == "complete":
                state = await complete_node(state, orch)
            else:
                state = await rollback_node(state, orch)
        else:
            state = await rollback_node(state, orch)

        return state
