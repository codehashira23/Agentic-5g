"""
Workflow node functions — one async function per lifecycle stage.

Each node:
  1. Sets state.stage and emits WORKFLOW_STAGE_CHANGED
  2. Calls the bound agent for a structured output
  3. Updates WorkflowState
  4. Appends a TraceEntry
  5. Returns the mutated state (LangGraph requirement)

Nodes are thin (WP2): cognition → agent, actions → SEL invoker.
Owning docs: 13-workflow-engine.md §6
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.application.workflow.state import TraceEntry, WorkflowState
from app.domain.agents.models import (
    Observation,
    Plan,
    StepResult,
    Validation,
    WorkflowSummary,
)

logger = logging.getLogger(__name__)


def _ts() -> str:
    return datetime.now(UTC).isoformat()


def _append_trace(
    state: WorkflowState,
    stage: str,
    agent_role: str,
    output: Any,
    latency_ms: float = 0.0,
) -> None:
    rationale = ""
    structured: dict[str, Any] = {}
    if hasattr(output, "rationale"):
        rationale = output.rationale
    if hasattr(output, "model_dump"):
        structured = output.model_dump()
    elif isinstance(output, dict):
        structured = output
    state.trace.append(TraceEntry(
        stage=stage,
        agent_role=agent_role,
        rationale=rationale,
        structured=structured,
        latency_ms=latency_ms,
        ts=_ts(),
    ))


# ---------------------------------------------------------------------------
# Observe node
# ---------------------------------------------------------------------------
async def observe_node(
    state: WorkflowState,
    orchestrator: Any,
) -> WorkflowState:
    state.stage = "observe"

    snapshot = orchestrator.twin_service.snapshot()
    snap_dict = {
        "tick": snapshot.tick,
        "health_pct": snapshot.health_pct,
        "nf_states": snapshot.nf_states,
    }
    state.before_snapshot = snap_dict

    obs: Observation = await orchestrator.observer.run({
        "tick": snapshot.tick,
        "goal": state.goal,
        "entity_states": snapshot.nf_states,
        "notable_events": [],
        "memory_summary": state.memory_context.get("summary", ""),
    }, orchestrator.make_context("observer"))

    state.observation = obs.model_dump()
    _append_trace(state, "observe", "observer", obs)
    return state


# ---------------------------------------------------------------------------
# Reason node
# ---------------------------------------------------------------------------
async def reason_node(
    state: WorkflowState,
    orchestrator: Any,
) -> WorkflowState:
    state.stage = "reason"

    from app.domain.agents.models import Interpretation
    interp: Interpretation = await orchestrator.interpreter.run({
        "goal": state.goal,
        "observation": state.observation,
        "memory_context": state.memory_context,
    }, orchestrator.make_context("planner"))

    state.interpretation = interp.model_dump()
    _append_trace(state, "reason", "planner", interp)
    return state


# ---------------------------------------------------------------------------
# Plan node
# ---------------------------------------------------------------------------
async def plan_node(
    state: WorkflowState,
    orchestrator: Any,
) -> WorkflowState:
    state.stage = "plan"

    catalog_names = [d.name for d in orchestrator.registry.all()]

    plan: Plan = await orchestrator.planner.run({
        "goal": state.goal,
        "interpretation": state.interpretation,
        "service_catalog": catalog_names,
        "memory_context": state.memory_context,
    }, orchestrator.make_context("planner"))

    state.plan = plan.model_dump()
    state.cursor = 0
    _append_trace(state, "plan", "planner", plan)
    return state


# ---------------------------------------------------------------------------
# Execute node
# ---------------------------------------------------------------------------
async def execute_node(
    state: WorkflowState,
    orchestrator: Any,
) -> WorkflowState:
    state.stage = "execute"

    steps = state.plan.get("steps", [])
    if state.cursor >= len(steps):
        # Plan exhausted — move to validate
        return state

    current_step = steps[state.cursor]

    result: StepResult = await orchestrator.executor.run({
        "current_step": current_step,
        "prior_results": state.results,
        "attempts": state.attempts,
        "retry_hint": None,
    }, orchestrator.make_context("executor"))

    state.attempts += 1

    # Record compensation for rollback
    if result.compensation:
        state.compensations.append(result.compensation.model_dump())

    state.results.append(result.model_dump())
    _append_trace(state, "execute", "executor", result)

    # Also actually invoke the service via the SEL invoker
    if result.status == "ok":
        try:
            await orchestrator.invoker.invoke(
                name=current_step.get("service", ""),
                args=current_step.get("args", {}),
                caller="executor",
                correlation_id=state.id,
                snapshot=state.observation.get("entity_states"),
            )
        except Exception as exc:
            logger.warning("Step %d service call failed: %s", state.cursor, exc)

    return state


# ---------------------------------------------------------------------------
# Validate node
# ---------------------------------------------------------------------------
async def validate_node(
    state: WorkflowState,
    orchestrator: Any,
) -> WorkflowState:
    state.stage = "validate"

    success_criteria = state.plan.get("success_criteria", [])
    snapshot = orchestrator.twin_service.snapshot()

    validation: Validation = await orchestrator.validator.run({
        "success_criteria": success_criteria,
        "current_state": {
            "tick": snapshot.tick,
            "nf_states": snapshot.nf_states,
        },
        "step_results": state.results,
    }, orchestrator.make_context("observer"))

    state.validation = validation.model_dump()
    _append_trace(state, "validate", "observer", validation)
    return state


# ---------------------------------------------------------------------------
# Complete node
# ---------------------------------------------------------------------------
async def complete_node(
    state: WorkflowState,
    orchestrator: Any,
) -> WorkflowState:
    state.stage = "complete"

    after_snapshot = orchestrator.twin_service.snapshot()

    summary: WorkflowSummary = await orchestrator.documenter.run({
        "workflow_id": state.id,
        "goal": state.goal,
        "trace": [t.model_dump() for t in state.trace],
        "step_results": state.results,
        "before_snapshot": state.before_snapshot,
        "after_snapshot": {
            "tick": after_snapshot.tick,
            "health_pct": after_snapshot.health_pct,
        },
    }, orchestrator.make_context("documentation"))

    state.summary = summary.model_dump()
    state.status = "completed"
    _append_trace(state, "complete", "documentation", summary)
    return state


# ---------------------------------------------------------------------------
# Rollback node
# ---------------------------------------------------------------------------
async def rollback_node(
    state: WorkflowState,
    orchestrator: Any,
) -> WorkflowState:
    """
    Execute compensations in reverse order.
    The Recovery agent builds the recovery plan; the Executor-like
    flow runs each compensation via the SEL invoker.
    """
    state.stage = "rollback"

    failure_reason = state.validation.get("rationale", "Unrecoverable failure")

    # Let the Recovery agent build a plan
    recovery_output = await orchestrator.recovery.run({
        "failure_context": failure_reason,
        "compensations": list(reversed(state.compensations)),
        "snapshot": state.observation.get("entity_states", {}),
    }, orchestrator.make_context("recovery"))

    # Execute compensations in reverse order via the SEL invoker
    for comp in recovery_output.steps:
        try:
            await orchestrator.invoker.invoke(
                name=comp.service,
                args={**comp.args, "target": comp.args.get("target", "")},
                caller="recovery",
                correlation_id=state.id,
            )
        except Exception as exc:
            logger.warning("Compensation %s failed: %s", comp.service, exc)

    if recovery_output.escalate:
        state.status = "failed"
        state.error = recovery_output.escalate_reason or failure_reason
    else:
        state.status = "failed"
        state.error = failure_reason

    state.recovery = recovery_output.model_dump()
    _append_trace(state, "rollback", "recovery", recovery_output)
    return state
