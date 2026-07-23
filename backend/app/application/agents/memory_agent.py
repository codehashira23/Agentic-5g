"""Memory agent — cross-cutting memory curation (sole writer)."""
from __future__ import annotations

from typing import Any

from app.application.agents.base import BaseAgent
from app.domain.agents.models import AgentRole, RetrievalResult


class MemoryAgent(BaseAgent[RetrievalResult]):
    """Retrieves relevant memory context (read path)."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.MEMORY

    @property
    def output_schema(self) -> type[RetrievalResult]:
        return RetrievalResult

    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "retrieve",
            "goal": input_data.get("goal", ""),
            "observation_summary": input_data.get("observation_summary", ""),
        }
