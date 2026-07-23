"""Optimizer agent — advises the Planner with ranked proposals."""
from __future__ import annotations

from typing import Any

from app.application.agents.base import BaseAgent
from app.domain.agents.models import AgentRole, OptimizationProposal


class OptimizerAgent(BaseAgent[OptimizationProposal]):
    @property
    def role(self) -> AgentRole:
        return AgentRole.OPTIMIZER

    @property
    def output_schema(self) -> type[OptimizationProposal]:
        return OptimizationProposal

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "optimize",
            "objective": input_data.get("objective", ""),
            "analytics": input_data.get("analytics", {}),
            "constraints": input_data.get("constraints", []),
        }
