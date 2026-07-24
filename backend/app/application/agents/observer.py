"""Observer agent — Observe and Validate stages."""
from __future__ import annotations

from typing import Any

from app.application.agents.base import AgentContext, BaseAgent
from app.domain.agents.models import (
    AgentRole,
    Observation,
    Validation,
)


class ObserverAgent(BaseAgent[Observation]):
    """Produces an Observation at the Observe stage."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.OBSERVER

    @property
    def output_schema(self) -> type[Observation]:
        return Observation

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # Slim down entity_states — only send status + load per NF, not full KPIs
        # Full KPI data can exceed Groq's context window on llama-3.1-8b-instant
        raw_states = input_data.get("entity_states", {})
        slim_states = {
            nf_id: {
                "type": s.get("type", ""),
                "region": s.get("region", ""),
                "status": s.get("status", "ACTIVE"),
                "load": round(s.get("load", 0.0), 2),
            }
            for nf_id, s in raw_states.items()
        }
        return {
            "task": "observe",
            "tick": input_data.get("tick", 0),
            "goal": input_data.get("goal", ""),
            "entity_states": slim_states,
            "notable_events": input_data.get("notable_events", []),
            "memory_summary": input_data.get("memory_summary", ""),
        }


class ValidatorAgent(BaseAgent[Validation]):
    """Produces a Validation at the Validate stage."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.OBSERVER

    @property
    def output_schema(self) -> type[Validation]:
        return Validation

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "validate",
            "success_criteria": input_data.get("success_criteria", []),
            "current_state": input_data.get("current_state", {}),
            "step_results": input_data.get("step_results", []),
        }

    async def run_validation(
        self,
        success_criteria: list[str],
        snapshot: dict[str, Any],
        step_results: list[dict[str, Any]],
        ctx: AgentContext,
    ) -> Validation:
        """Convenience method: validate from criteria + snapshot."""
        return await self.run({
            "success_criteria": success_criteria,
            "current_state": snapshot,
            "step_results": step_results,
        }, ctx)
