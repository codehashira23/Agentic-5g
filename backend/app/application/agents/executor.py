"""Executor agent — Execute and Retry stages."""
from __future__ import annotations

from typing import Any

from app.application.agents.base import BaseAgent
from app.domain.agents.models import AgentRole, StepResult


class ExecutorAgent(BaseAgent[StepResult]):
    """Executes one plan step; records compensation on success."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.EXECUTOR

    @property
    def output_schema(self) -> type[StepResult]:
        return StepResult

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "execute",
            "current_step": input_data.get("current_step", {}),
            "prior_results": input_data.get("prior_results", []),
            "attempts": input_data.get("attempts", 0),
            "retry_hint": input_data.get("retry_hint", None),
        }
