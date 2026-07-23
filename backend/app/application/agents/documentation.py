"""Documentation agent — Complete stage."""
from __future__ import annotations

from typing import Any

from app.application.agents.base import BaseAgent
from app.domain.agents.models import AgentRole, WorkflowSummary


class DocumentationAgent(BaseAgent[WorkflowSummary]):
    """Produces a WorkflowSummary at the Complete stage."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.DOCUMENTATION

    @property
    def output_schema(self) -> type[WorkflowSummary]:
        return WorkflowSummary

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "document",
            "workflow_id": input_data.get("workflow_id", ""),
            "goal": input_data.get("goal", ""),
            "trace": input_data.get("trace", []),
            "step_results": input_data.get("step_results", []),
            "before_snapshot": input_data.get("before_snapshot", {}),
            "after_snapshot": input_data.get("after_snapshot", {}),
        }
