"""Planner agent — Reason and Plan stages."""
from __future__ import annotations

from typing import Any

from app.application.agents.base import BaseAgent
from app.domain.agents.models import AgentRole, Interpretation, Plan


class InterpretationAgent(BaseAgent[Interpretation]):
    """Produces an Interpretation at the Reason stage."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.PLANNER

    @property
    def output_schema(self) -> type[Interpretation]:
        return Interpretation

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "reason",
            "goal": input_data.get("goal", ""),
            "observation": input_data.get("observation", {}),
            "memory_context": input_data.get("memory_context", {}),
        }


class PlannerAgent(BaseAgent[Plan]):
    """Produces a Plan at the Plan stage."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.PLANNER

    @property
    def output_schema(self) -> type[Plan]:
        return Plan

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "plan",
            "goal": input_data.get("goal", ""),
            "interpretation": input_data.get("interpretation", {}),
            # Send only the first 25 most relevant services to avoid token overflow
            "service_catalog": input_data.get("service_catalog", [])[:25],
            "memory_context": input_data.get("memory_context", {}),
            "optimization_proposal": input_data.get("optimization", None),
        }
