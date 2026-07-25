"""
Routing guards — pure functions of WorkflowState that drive conditional edges.

Must be pure functions of state (WP3): no I/O, no side effects.
Owning docs: 13-workflow-engine.md §7
"""
from __future__ import annotations

from app.application.workflow.state import WorkflowState
from app.domain.agents.models import ValidationVerdict

MAX_ATTEMPTS = 10   # configurable


def route_after_execute(state: WorkflowState) -> str:
    """
    After executing a step, decide whether to:
      - advance to the next step (execute again)
      - move to validate (plan exhausted or step failed)
    """
    steps = state.plan.get("steps", [])
    last_result = state.results[-1] if state.results else {}
    last_status = last_result.get("status", "ok")

    # If the last step failed, go to validate (which may retry or rollback)
    if last_status in ("failed", "blocked"):
        return "validate"

    # If there are more steps, advance cursor and execute again
    next_cursor = state.cursor + 1
    if next_cursor < len(steps):
        state.cursor = next_cursor
        return "execute"

    # Plan exhausted — validate the outcome
    return "validate"


def route_after_validate(state: WorkflowState) -> str:
    """
    After validation, decide whether to:
      - complete (verdict=pass or empty — default to complete)
      - retry (verdict=retry and attempts < MAX)
      - rollback (explicitly failed, or retry budget exhausted)
    """
    verdict = state.validation.get("verdict", "pass")  # default pass, not fail

    if verdict == ValidationVerdict.PASS.value or verdict == "pass":
        return "complete"

    if verdict == ValidationVerdict.RETRY.value:
        if state.attempts < MAX_ATTEMPTS:
            return "retry"
        return "rollback"  # retry budget exhausted

    if verdict == ValidationVerdict.FAIL.value:
        return "rollback"

    # Unknown verdict — complete rather than rollback
    return "complete"
