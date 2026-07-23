"""
WorkflowState — the single shared object threaded through the LangGraph.

Checkpointed by LangGraph after every node.
All fields are JSON-serialisable for checkpoint persistence.
Owning docs: 13-workflow-engine.md §4
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Lifecycle stage names (must match the LangGraph node names)
Stage = Literal[
    "observe", "reason", "plan", "execute",
    "validate", "retry", "rollback", "complete",
]

WorkflowStatus = Literal[
    "running", "completed", "failed", "cancelled", "paused",
]


class WorkflowConfig(BaseModel):
    """Experiment toggles (12-database.md DP7, 02-research-background §16)."""
    multi_agent: bool = True
    memory_on: bool = True
    recovery_on: bool = True
    policy_on: bool = True


class TraceEntry(BaseModel):
    """One reasoning/execution trace row (maps to workflow_trace table)."""
    stage: str
    agent_role: str
    rationale: str = ""
    structured: dict[str, Any] = Field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    ts: str = ""


class WorkflowState(BaseModel):
    """
    The complete, serialisable state object for one workflow run.
    Flows through every LangGraph node; checkpointed after each.
    """

    # Identity
    id: str                          # wf_{uuid} == correlation_id
    goal: str
    trigger: str = "user"            # user | observer | template
    seed: int = 42
    scenario: str = "baseline_healthy"
    config: WorkflowConfig = Field(default_factory=WorkflowConfig)

    # Lifecycle
    stage: Stage = "observe"
    status: WorkflowStatus = "running"
    attempts: int = 0                # total action attempts (bounded)

    # Agent outputs (structured — from domain/agents/models.py)
    observation: dict[str, Any] = Field(default_factory=dict)
    interpretation: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] = Field(default_factory=dict)   # Plan.model_dump()
    cursor: int = 0                  # current step index
    results: list[dict[str, Any]] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)

    # Recovery
    compensations: list[dict[str, Any]] = Field(default_factory=list)
    recovery: dict[str, Any] = Field(default_factory=dict)

    # Memory context (set by Memory agent)
    memory_context: dict[str, Any] = Field(default_factory=dict)

    # Output
    summary: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    # Trace (append-only; also written to workflow_trace table)
    trace: list[TraceEntry] = Field(default_factory=list)

    # Before snapshot (saved at Observe for Documentation's before/after diff)
    before_snapshot: dict[str, Any] = Field(default_factory=dict)
