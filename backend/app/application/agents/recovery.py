"""Recovery agent — Rollback stage."""
from __future__ import annotations

from typing import Any

from app.application.agents.base import BaseAgent
from app.domain.agents.models import AgentRole, RecoveryPlan


class RecoveryAgent(BaseAgent[RecoveryPlan]):
    @property
    def role(self) -> AgentRole:
        return AgentRole.RECOVERY

    @property
    def output_schema(self) -> type[RecoveryPlan]:
        return RecoveryPlan

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "recover",
            "failure_context": input_data.get("failure_context", ""),
            "compensations": input_data.get("compensations", []),
            "snapshot": input_data.get("snapshot", {}),
        }
