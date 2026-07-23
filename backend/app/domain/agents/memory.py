"""
Domain: Agent memory value objects — MemoryRecord and KnowledgeEdge.

These are the persistent memory representations stored in the DB
(12-database.md §6.13-§6.15) and manipulated by the Memory agent.

Three memory tiers (05-agents.md §6):
  working   — ephemeral within a workflow (in WorkflowState)
  episodic  — one record per completed/failed workflow
  semantic  — durable reusable facts (distilled from episodic patterns)

Knowledge graph:
  KnowledgeNode + KnowledgeEdge — entities and typed relations

Rules:
  - Pure Python + Pydantic only. Zero framework imports.
  - Immutable value objects (frozen=True).
  - Only the Memory agent holds memory-write tools (AP1 / 05-agents.md §4).

Owning docs: 05-agents.md §6, 12-database.md §6.13-§6.15
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.agents.models import MemoryScope


# ---------------------------------------------------------------------------
# MemoryRecord — one durable memory entry
# ---------------------------------------------------------------------------
class MemoryRecord(BaseModel):
    """
    A single stored memory record (episodic or semantic).

    The `weight` field decays over time for semantic memories — low-weight
    facts are candidates for pruning (12-database.md §9).
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="'mem_{uuid}'")
    scope: MemoryScope
    content: dict[str, Any]
    summary: str = Field(..., description="Short searchable text")

    provenance_workflow_id: str | None = None
    created_by_agent: str = "memory"
    weight: float = Field(default=1.0, ge=0.0, le=1.0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    expires_at: datetime | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        _now = now or datetime.now(UTC)
        return _now >= self.expires_at

    def decay(self, factor: float = 0.95) -> MemoryRecord:
        """Return a new record with a reduced weight (semantic decay)."""
        return self.model_copy(update={"weight": max(0.0, self.weight * factor)})


# ---------------------------------------------------------------------------
# KnowledgeNode — an entity in the knowledge graph
# ---------------------------------------------------------------------------
class KnowledgeEntityType(str):
    """Allowed entity types (open string set for extensibility)."""
    NF = "nf"
    MODEL = "model"
    INCIDENT = "incident"
    INTENT = "intent"
    REGION = "region"
    POLICY = "policy"


class KnowledgeNode(BaseModel):
    """
    A node in the agent knowledge graph.

    Natural ids are preferred (e.g. 'nf:upf_delhi_1', 'incident:inc_001')
    over random UUIDs so the graph is readable and deduplication is easy.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="e.g. 'nf:upf_delhi_1', 'model:congestion-det'")
    entity_type: str = Field(..., description="One of KnowledgeEntityType values")
    label: str
    props: dict[str, Any] = Field(default_factory=dict)

    first_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    def with_props(self, **new_props: Any) -> KnowledgeNode:
        merged = {**self.props, **new_props}
        return self.model_copy(update={
            "props": merged,
            "updated_at": datetime.now(UTC),
        })


# ---------------------------------------------------------------------------
# KnowledgeEdge — a typed relation between two nodes
# ---------------------------------------------------------------------------
class KnowledgeEdge(BaseModel):
    """
    A directed, typed relation between two knowledge-graph nodes.

    Provenance links every edge back to the workflow that created it,
    enabling the UI to show "this relation was established by wf_abc".
    """

    model_config = {"frozen": True}

    src_id: str
    relation: str = Field(
        ...,
        description="Snake_case verb, e.g. 'hosted_on', 'caused_by', 'mitigated_by'",
    )
    dst_id: str
    props: dict[str, Any] = Field(default_factory=dict)

    provenance_workflow_id: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @property
    def key(self) -> tuple[str, str, str]:
        """Unique key for upsert deduplication: (src, relation, dst)."""
        return (self.src_id, self.relation, self.dst_id)
