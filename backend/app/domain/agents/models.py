"""
Domain: Agent structured I/O models.

Every agent receives typed input and MUST return a validated Pydantic object.
These are the output schemas for the seven agent roles (05-agents.md §12).

Rules:
  - Pure Python + Pydantic only. Zero framework imports.
  - Every output includes a mandatory `rationale` field (AP5 / PP6).
  - These models are the hand-off contracts between agents and the workflow
    engine (13-workflow-engine.md §4 — WorkflowState fields).
  - Immutable (frozen=True) where the object is passed between agents;
    mutable lists are used for accumulation within a single stage.

Owning docs: 05-agents.md §12, 13-workflow-engine.md §4
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared base — every agent output carries a rationale
# ---------------------------------------------------------------------------
class AgentOutput(BaseModel):
    """Base class for all agent structured outputs."""

    model_config = {"frozen": True}

    rationale: str = Field(
        ...,
        description="1-3 sentences explaining the decision, citing tool results",
        min_length=1,
    )


# ---------------------------------------------------------------------------
# AgentRole — the seven agent roles
# ---------------------------------------------------------------------------
class AgentRole(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    OBSERVER = "observer"
    OPTIMIZER = "optimizer"
    RECOVERY = "recovery"
    DOCUMENTATION = "documentation"
    MEMORY = "memory"


# ---------------------------------------------------------------------------
# Observer outputs
# ---------------------------------------------------------------------------
class Observation(AgentOutput):
    """
    Observer → Planner hand-off (Observe stage).
    Facts only — no speculation.
    """

    tick: int = Field(..., ge=0)
    health_pct: float = Field(..., ge=0.0, le=1.0)
    active_workflows: int = Field(default=0, ge=0)

    # Key entity states relevant to the current goal
    entity_states: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of relevant NF states from twin.snapshot",
    )
    # Notable recent events (breach, failure, etc.)
    notable_events: list[str] = Field(
        default_factory=list,
        description="Short descriptions of relevant recent events",
    )
    # Retrieved memory context (set by Memory agent before Planner runs)
    memory_summary: str = ""


class ValidationVerdict(str, Enum):
    PASS = "pass"
    RETRY = "retry"
    FAIL = "fail"


class CriterionResult(BaseModel):
    """One success criterion evaluated against current twin state."""

    model_config = {"frozen": True}

    criterion: str
    met: bool
    evidence: str = ""


class Validation(AgentOutput):
    """
    Observer → Workflow engine (Validate stage).
    Verdict drives the conditional edge: pass / retry / fail.
    """

    verdict: ValidationVerdict
    criteria: list[CriterionResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Planner outputs
# ---------------------------------------------------------------------------
class Interpretation(AgentOutput):
    """
    Planner → Plan stage (Reason stage output).
    Structured decomposition of the intent.
    """

    objective: str = Field(default="", description="What needs to be achieved")
    targets: list[str] = Field(
        default_factory=list,
        description="Target entity ids or regions",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Constraints the plan must respect",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Verifiable conditions the Observer will check",
    )


class Step(BaseModel):
    """One ordered step in a Plan."""

    model_config = {"frozen": True}

    index: int = Field(..., ge=0)
    service: str = Field(..., description="Dotted service name, e.g. 'nrf.discover'")
    args: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(
        default_factory=list,
        description="Indices of steps that must complete before this one",
    )
    success_criterion: str = Field(
        default="",
        description="How the Executor verifies this step succeeded",
    )


class Plan(AgentOutput):
    """
    Planner → Executor hand-off (Plan stage output).
    Ordered steps with dependencies and success criteria.
    """

    steps: list[Step] = Field(default_factory=list)
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Top-level criteria the Observer validates at the end",
    )

    def step_count(self) -> int:
        return len(self.steps)

    def has_cycles(self) -> bool:
        """Return True if the dependency graph has a cycle (invalid plan)."""
        visited: set[int] = set()
        stack: set[int] = set()

        def dfs(idx: int) -> bool:
            visited.add(idx)
            stack.add(idx)
            step_map = {s.index: s for s in self.steps}
            for dep in step_map.get(idx, Step(index=idx, service="")).depends_on:
                if dep not in visited and dfs(dep):
                    return True
                if dep in stack:
                    return True
            stack.discard(idx)
            return False

        for step in self.steps:
            if step.index not in visited:
                if dfs(step.index):
                    return True
        return False

    def all_services_in_catalog(self, catalog: set[str]) -> bool:
        """Return True if every step's service exists in the given catalog."""
        return all(s.service in catalog for s in self.steps)


# ---------------------------------------------------------------------------
# Executor outputs
# ---------------------------------------------------------------------------
class Compensation(BaseModel):
    """The inverse action to undo a successful step (Recovery uses this)."""

    model_config = {"frozen": True}

    service: str
    args: dict[str, Any] = Field(default_factory=dict)
    step_index: int


class StepResult(AgentOutput):
    """
    Executor → Workflow state (per-step result during Execute stage).
    """

    step_index: int
    service: str
    status: str = Field(
        ...,
        description="'ok' | 'failed' | 'blocked'",
    )
    result: dict[str, Any] = Field(default_factory=dict)
    success_met: bool = False
    compensation: Compensation | None = None
    retry_hint: dict[str, Any] | None = Field(
        default=None,
        description="Adjusted args or alternative service for retry",
    )


# ---------------------------------------------------------------------------
# Optimizer output
# ---------------------------------------------------------------------------
class OptimizationOption(BaseModel):
    """One ranked option in an OptimizationProposal."""

    model_config = {"frozen": True}

    rank: int = Field(..., ge=1)
    actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="[{service, args}, ...] to execute",
    )
    expected_impact: str = ""
    risk: str = "low"


class OptimizationProposal(AgentOutput):
    """
    Optimizer → Planner (optional, advises the plan).
    Ranked list of action sets that improve the objective.
    """

    objective: str
    options: list[OptimizationOption] = Field(default_factory=list)

    def best_option(self) -> OptimizationOption | None:
        if not self.options:
            return None
        return min(self.options, key=lambda o: o.rank)


# ---------------------------------------------------------------------------
# Recovery outputs
# ---------------------------------------------------------------------------
class CompensationResult(BaseModel):
    """Result of executing one compensation action in Rollback."""

    model_config = {"frozen": True}

    service: str
    status: str  # "ok" | "failed"
    note: str = ""


class RecoveryPlan(AgentOutput):
    """
    Recovery agent → Rollback stage.
    The reverse-ordered compensation steps + escalation flag.
    """

    steps: list[Compensation] = Field(default_factory=list)
    escalate: bool = False
    escalate_reason: str = ""


# ---------------------------------------------------------------------------
# Documentation output
# ---------------------------------------------------------------------------
class KGDelta(BaseModel):
    """One knowledge-graph relation proposed by the Documentation agent."""

    model_config = {"frozen": True}

    src: str   # entity id
    relation: str  # e.g. "hosted_on", "caused_by", "mitigated_by"
    dst: str
    props: dict[str, Any] = Field(default_factory=dict)


class WorkflowSummary(AgentOutput):
    """
    Documentation agent → Memory agent (Complete stage).
    Faithful narrative of what the workflow did.
    """

    workflow_id: str
    goal: str
    outcome: str  # "success" | "failed"
    narrative: str = Field(..., description="Plain-language summary of actions/outcomes")
    evidence: list[str] = Field(
        default_factory=list,
        description="KPI/state values that confirm the outcome",
    )
    lessons: list[str] = Field(default_factory=list)
    kg_deltas: list[KGDelta] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Memory agent I/O
# ---------------------------------------------------------------------------
class MemoryScope(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryWrite(BaseModel):
    """One memory record to write (Memory agent is sole writer)."""

    model_config = {"frozen": True}

    scope: MemoryScope
    content: dict[str, Any]
    summary: str = Field(..., description="Short searchable text")
    provenance_workflow_id: str | None = None


class KnowledgeDelta(BaseModel):
    """Proposed knowledge-graph upserts from Documentation / Recovery."""

    model_config = {"frozen": True}

    upserts: list[KGDelta] = Field(default_factory=list)


class RetrievalResult(AgentOutput):
    """
    Memory agent → requesting agent (read path).
    Returns relevant memories and KG neighbourhood.
    """

    episodic: list[dict[str, Any]] = Field(default_factory=list)
    semantic: list[dict[str, Any]] = Field(default_factory=list)
    kg_neighbourhood: dict[str, Any] = Field(default_factory=dict)
