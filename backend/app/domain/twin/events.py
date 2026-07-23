"""
Domain: Event types emitted by the Digital Twin.

Defines:
  - EventType    : the canonical SCREAMING_SNAKE_CASE enum of all event names
  - DomainEvent  : the base event (the canonical envelope from 03-architecture.md §24)
  - Specific event payload dataclasses for every event type

Rules (Clean Architecture):
  - Pure Python + Pydantic only. Zero framework imports.
  - Events are immutable value objects (frozen=True).
  - Every event carries: type, correlation_id, ts (UTC), tick, payload fields.

Event taxonomy matches 06-digital-twin.md §14 and 09-api.md §10 (WS stream).
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# EventType — canonical enum (SCREAMING_SNAKE_CASE, 15-kiro-rules.md §8)
# ---------------------------------------------------------------------------
class EventType(str, Enum):
    """Every event type that can be emitted in Agent5G."""

    # --- Simulation clock ---
    SIM_TICK = "SIM_TICK"

    # --- KPI events ---
    KPI_UPDATED = "KPI_UPDATED"
    KPI_THRESHOLD_BREACH = "KPI_THRESHOLD_BREACH"
    KPI_THRESHOLD_CLEARED = "KPI_THRESHOLD_CLEARED"

    # --- NF lifecycle ---
    NF_REGISTERED = "NF_REGISTERED"
    NF_DEREGISTERED = "NF_DEREGISTERED"
    NF_FAILED = "NF_FAILED"
    NF_RECOVERED = "NF_RECOVERED"

    # --- UE / session ---
    UE_ATTACHED = "UE_ATTACHED"
    UE_HANDOVER = "UE_HANDOVER"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_RELEASED = "SESSION_RELEASED"

    # --- AI/ML model lifecycle ---
    MODEL_DEPLOYED = "MODEL_DEPLOYED"
    MODEL_RETIRED = "MODEL_RETIRED"

    # --- Data collection ---
    DATA_COLLECTED = "DATA_COLLECTED"

    # --- SEL / service calls (emitted by the invoker, not the twin) ---
    SERVICE_CALLED = "SERVICE_CALLED"
    SERVICE_RESULT = "SERVICE_RESULT"
    POLICY_BLOCKED = "POLICY_BLOCKED"

    # --- Workflow lifecycle ---
    WORKFLOW_STAGE_CHANGED = "WORKFLOW_STAGE_CHANGED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"


# ---------------------------------------------------------------------------
# DomainEvent — the canonical base envelope
# (03-architecture.md §24: {type, correlation_id, ts, payload})
# ---------------------------------------------------------------------------
class DomainEvent(BaseModel):
    """
    The canonical event envelope.  Every event in the system is a subclass.

    Fields shared by all events:
      type           : what kind of event this is
      event_id       : unique id for this event instance
      correlation_id : the workflow/request that caused it (wf_uuid or None)
      ts             : wall-clock UTC timestamp
      tick           : simulation tick (0 for non-simulation events)
    """

    model_config = {"frozen": True}

    type: EventType
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tick: int = Field(default=0, ge=0)

    def to_envelope(self) -> dict[str, Any]:
        """
        Serialize to the canonical WS/bus JSON envelope.
        Used by the event bus and WebSocket hub.
        """
        return {
            "type": self.type.value,
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "ts": self.ts.isoformat(),
            "tick": self.tick,
            "payload": self.model_dump(
                exclude={"type", "event_id", "correlation_id", "ts", "tick"}
            ),
        }


# ---------------------------------------------------------------------------
# Simulation clock
# ---------------------------------------------------------------------------
class SimTickEvent(DomainEvent):
    """Emitted by the SimScheduler on every simulation tick."""

    type: EventType = EventType.SIM_TICK
    sim_time: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# KPI events
# ---------------------------------------------------------------------------
class KpiUpdatedEvent(DomainEvent):
    """Emitted (batched/downsampled) when a KPI value changes."""

    type: EventType = EventType.KPI_UPDATED
    entity_id: str
    kpi: str          # KpiName value
    value: float


class KpiThresholdBreachEvent(DomainEvent):
    """
    Emitted when a KPI crosses its HIGH threshold (lossless — never dropped).
    Triggers autonomous workflows in the Observer agent.
    """

    type: EventType = EventType.KPI_THRESHOLD_BREACH
    entity_id: str
    kpi: str
    value: float
    threshold: float
    region: str


class KpiThresholdClearedEvent(DomainEvent):
    """Emitted when a breaching KPI drops below its LOW threshold."""

    type: EventType = EventType.KPI_THRESHOLD_CLEARED
    entity_id: str
    kpi: str
    value: float
    region: str


# ---------------------------------------------------------------------------
# NF lifecycle events
# ---------------------------------------------------------------------------
class NfRegisteredEvent(DomainEvent):
    """Emitted when an NF registers with the NRF."""

    type: EventType = EventType.NF_REGISTERED
    entity_id: str
    nf_type: str      # NFType value


class NfDeregisteredEvent(DomainEvent):
    """Emitted when an NF deregisters from the NRF."""

    type: EventType = EventType.NF_DEREGISTERED
    entity_id: str
    nf_type: str


class NfFailedEvent(DomainEvent):
    """
    Emitted when an NF transitions to FAILED state (lossless).
    May be caused by a stochastic hazard or a fault injection.
    """

    type: EventType = EventType.NF_FAILED
    entity_id: str
    nf_type: str
    cause: str = "unknown"     # "hazard" | "injected" | ...


class NfRecoveredEvent(DomainEvent):
    """Emitted when an NF returns to ACTIVE state."""

    type: EventType = EventType.NF_RECOVERED
    entity_id: str
    nf_type: str


# ---------------------------------------------------------------------------
# UE / session events
# ---------------------------------------------------------------------------
class UeAttachedEvent(DomainEvent):
    """Emitted when a UE attaches to a gNB."""

    type: EventType = EventType.UE_ATTACHED
    ue_id: str
    gnb_id: str
    region: str


class UeHandoverEvent(DomainEvent):
    """Emitted when a UE moves between gNBs."""

    type: EventType = EventType.UE_HANDOVER
    ue_id: str
    from_gnb: str
    to_gnb: str
    region: str


class SessionCreatedEvent(DomainEvent):
    """Emitted when a PDU session is established."""

    type: EventType = EventType.SESSION_CREATED
    session_id: str
    ue_id: str
    smf_id: str
    upf_id: str


class SessionReleasedEvent(DomainEvent):
    """Emitted when a PDU session is released."""

    type: EventType = EventType.SESSION_RELEASED
    session_id: str
    ue_id: str


# ---------------------------------------------------------------------------
# AI/ML model lifecycle events
# ---------------------------------------------------------------------------
class ModelDeployedEvent(DomainEvent):
    """
    Emitted when an AIMLE model is successfully deployed to a target NF/Edge
    (lossless — drives the UI Model Manager and the Topology badge).
    """

    type: EventType = EventType.MODEL_DEPLOYED
    model_id: str
    model_name: str
    target_id: str    # NF/Edge id the model was deployed to
    region: str


class ModelRetiredEvent(DomainEvent):
    """Emitted when a model is retired from a target."""

    type: EventType = EventType.MODEL_RETIRED
    model_id: str
    target_id: str


# ---------------------------------------------------------------------------
# Data collection event
# ---------------------------------------------------------------------------
class DataCollectedEvent(DomainEvent):
    """Emitted by DCF when a collection cycle completes."""

    type: EventType = EventType.DATA_COLLECTED
    subscription_id: str
    producer_ids: tuple[str, ...] = ()
    sample_count: int = 0


# ---------------------------------------------------------------------------
# SEL / service call events (emitted by the invoker, not the twin)
# ---------------------------------------------------------------------------
class ServiceCalledEvent(DomainEvent):
    """Emitted just before a service is dispatched to the NF handler."""

    type: EventType = EventType.SERVICE_CALLED
    service_name: str
    caller: str       # "executor" | "recovery" | "api" | NF id
    args_summary: str = ""   # short human-readable summary (not the full args)


class ServiceResultEvent(DomainEvent):
    """Emitted after a service invocation completes (success or error)."""

    type: EventType = EventType.SERVICE_RESULT
    service_name: str
    status: str       # "ok" | "error"
    latency_ms: float = 0.0


class PolicyBlockedEvent(DomainEvent):
    """Emitted when the SEL policy engine blocks a service call (lossless)."""

    type: EventType = EventType.POLICY_BLOCKED
    service_name: str
    policy_id: str
    message: str


# ---------------------------------------------------------------------------
# Workflow lifecycle events
# ---------------------------------------------------------------------------
class WorkflowStageChangedEvent(DomainEvent):
    """Emitted by the workflow engine on every stage transition."""

    type: EventType = EventType.WORKFLOW_STAGE_CHANGED
    workflow_id: str
    from_stage: str
    to_stage: str
    status: str      # "running" | "paused" | ...


class WorkflowCompletedEvent(DomainEvent):
    """Emitted when a workflow reaches the Complete stage successfully."""

    type: EventType = EventType.WORKFLOW_COMPLETED
    workflow_id: str
    goal: str


class WorkflowFailedEvent(DomainEvent):
    """Emitted when a workflow terminates with an unrecoverable error."""

    type: EventType = EventType.WORKFLOW_FAILED
    workflow_id: str
    error: str
