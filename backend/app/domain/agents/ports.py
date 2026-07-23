"""
Domain: Ports (interfaces) for the Agent and Workflow layers.

Owning docs: 03-architecture.md §7, 05-agents.md §12, 12-database.md
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.domain.agents.memory import KnowledgeEdge, KnowledgeNode, MemoryRecord
from app.domain.agents.models import MemoryScope


# ---------------------------------------------------------------------------
# MemoryStore — port for agent memory persistence
# ---------------------------------------------------------------------------
@runtime_checkable
class MemoryStore(Protocol):
    """
    Port: persist and retrieve agent memory records and knowledge graph.
    Only the Memory agent may call write methods (AP1 / 05-agents.md §4).
    Implemented in infrastructure/db/repos/memory_store.py (C069).
    """

    # --- Records ---
    async def save_record(self, record: MemoryRecord) -> None:
        """Upsert a memory record by id."""
        ...

    async def get_records(
        self,
        scope: MemoryScope,
        limit: int = 20,
        workflow_id: str | None = None,
    ) -> list[MemoryRecord]:
        """Return memory records filtered by scope and optional workflow."""
        ...

    async def get_record(self, record_id: str) -> MemoryRecord | None:
        """Return one record by id."""
        ...

    # --- Knowledge graph ---
    async def upsert_node(self, node: KnowledgeNode) -> None:
        """Insert or update a knowledge-graph node."""
        ...

    async def upsert_edge(self, edge: KnowledgeEdge) -> None:
        """Insert or update a knowledge-graph edge (keyed by src/relation/dst)."""
        ...

    async def get_neighbourhood(
        self,
        node_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Return the nodes and edges reachable within `depth` hops."""
        ...


# ---------------------------------------------------------------------------
# WorkflowRepository — port for workflow state persistence
# ---------------------------------------------------------------------------
@runtime_checkable
class WorkflowRepository(Protocol):
    """
    Port: persist workflow rows, steps, and trace entries.
    Implemented in infrastructure/db/repos/workflow_repo.py (C069).
    """

    async def save_workflow(self, workflow_id: str, data: dict[str, Any]) -> None:
        """Upsert the `workflows` row."""
        ...

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Return the `workflows` row as a dict."""
        ...

    async def list_workflows(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return a paginated list of workflow rows."""
        ...

    async def append_trace(self, trace_row: dict[str, Any]) -> None:
        """Append one row to `workflow_trace`."""
        ...

    async def get_trace(self, workflow_id: str) -> list[dict[str, Any]]:
        """Return all trace rows for a workflow, ordered by ts."""
        ...

    async def save_step(self, step_row: dict[str, Any]) -> None:
        """Upsert one row in `workflow_steps`."""
        ...

    async def get_steps(self, workflow_id: str) -> list[dict[str, Any]]:
        """Return all step rows for a workflow."""
        ...


# ---------------------------------------------------------------------------
# LLMClient — port for model inference (live / record / replay)
# (03-architecture.md §7, 10-backend.md §8.4, 14-prompts.md §12)
# ---------------------------------------------------------------------------
@runtime_checkable
class LLMClient(Protocol):
    """
    Port: send prompts to an LLM and receive structured responses.
    Three modes behind this interface (10-backend.md §8.4):
      live   — real model call (free-tier provider)
      record — live + save request/response to fixtures
      replay — serve saved fixtures (offline, $0, deterministic)
    """

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Return the model's text completion."""
        ...

    async def tool_call(
        self,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        response_schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Run a tool-use turn and return the model's structured output.
        The model may call tools; this method handles the full loop.
        """
        ...


# ---------------------------------------------------------------------------
# Rng — port for the seeded random number generator
# (03-architecture.md §7, 06-digital-twin.md §13, GR4)
# ---------------------------------------------------------------------------
@runtime_checkable
class Rng(Protocol):
    """
    Port: seeded randomness source (GR4 — all entropy through one port).
    Implemented in infrastructure/rng/rng.py (C060).
    """

    def for_tick(self, tick: int) -> Any:
        """
        Return a per-tick RngStream derived from (seed, tick).
        Same (seed, tick) always produces the same stream — determinism.
        """
        ...

    def reseed(self, seed: int) -> None:
        """Replace the global seed (called on simulation reset)."""
        ...


# ---------------------------------------------------------------------------
# EventBus — port for in-process publish/subscribe
# (03-architecture.md §7-§8, 10-backend.md §8.3)
# ---------------------------------------------------------------------------
@runtime_checkable
class EventBus(Protocol):
    """
    Port: async publish/subscribe event bus.
    Persist-first then fan-out (03-architecture.md §8).
    Implemented in infrastructure/bus/bus.py (C065).
    """

    async def publish(self, event: Any) -> None:
        """Persist the event then fan it out to subscribers."""
        ...

    def subscribe(
        self,
        event_types: list[str],
        handler: Any,
    ) -> Any:
        """
        Register a handler for the given event types.
        Returns a Subscription object that can be used to unsubscribe.
        """
        ...
