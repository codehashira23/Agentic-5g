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
        raw_states = input_data.get("entity_states", {})
        goal = input_data.get("goal", "").lower()

        # Determine which regions are relevant to the goal
        relevant_regions: set[str] = set()
        if "delhi" in goal:
            relevant_regions.add("Delhi")
        if "mumbai" in goal:
            relevant_regions.add("Mumbai")
        if "core" in goal or not relevant_regions:
            relevant_regions.update({"Delhi", "Mumbai", "Core"})

        # Only include NFs relevant to the goal (UPF, Edge, gNB in target region)
        # Include actual KPI values so Groq can reference real numbers
        slim_states: dict[str, Any] = {}
        for nf_id, s in raw_states.items():
            region = s.get("region", "")
            nf_type = s.get("type", "")
            if region not in relevant_regions:
                continue
            # Include KPIs for data-plane nodes that matter for the goal
            entry: dict[str, Any] = {
                "type": nf_type,
                "region": region,
                "status": s.get("status", "ACTIVE"),
                "load": round(s.get("load", 0.0), 2),
            }
            kpis = s.get("kpis", {})
            if kpis and nf_type in ("UPF", "gNB", "Edge", "NWDAF"):
                kpi_summary: dict[str, Any] = {}
                for kpi_name, kpi_data in kpis.items():
                    if isinstance(kpi_data, dict):
                        val = kpi_data.get("current", 0)
                        breaching = kpi_data.get("breaching", False)
                        kpi_summary[kpi_name] = {
                            "value": round(float(val), 3),
                            "breaching": breaching,
                        }
                    else:
                        kpi_summary[kpi_name] = round(float(kpi_data), 3)
                if kpi_summary:
                    entry["kpis"] = kpi_summary
            slim_states[nf_id] = entry

        return {
            "task": "observe",
            "tick": input_data.get("tick", 0),
            "goal": input_data.get("goal", ""),
            "network_state": slim_states,
            "notable_events": input_data.get("notable_events", []),
            "memory_summary": input_data.get("memory_summary", ""),
        }


class ValidatorAgent(BaseAgent[Validation]):
    """Produces a Validation at the Validate stage."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.OBSERVER  # uses observer@v1 which has validate task handling

    @property
    def output_schema(self) -> type[Validation]:
        return Validation

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "validate",
            "goal": input_data.get("goal", ""),
            "success_criteria": input_data.get("success_criteria", []),
            "current_state": input_data.get("current_state", {}),
            "step_results": input_data.get("step_results", []),
            "instruction": "Return verdict=pass if step_results show any successful service calls or if no failures occurred. Only return fail if there is clear evidence of failure.",
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
