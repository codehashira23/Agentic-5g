"""
Domain: Service model — ServiceDescriptor, ServiceKind, Pattern, ServiceResult.

These are the core value objects for the Service Enablement Layer (SEL).
Every registered service has a descriptor; every invocation produces a result.

Rules:
  - Pure Python + Pydantic only. Zero framework imports.
  - Immutable value objects (frozen=True).
  - ServiceDescriptor is the single source of truth for service metadata,
    the agent tool schema, and the REST /services response.

Owning docs: 08-services.md §4-§5, 15-kiro-rules.md §8
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ServiceKind — what kind of action a service performs
# ---------------------------------------------------------------------------
class ServiceKind(str, Enum):
    READ = "read"       # side-effect-free; no policy check needed
    ACTION = "action"   # mutates twin state; policy-checked
    CONTROL = "control" # platform/sim control; UI-only, never agent tools


# ---------------------------------------------------------------------------
# Pattern — interaction style
# ---------------------------------------------------------------------------
class Pattern(str, Enum):
    REQUEST_RESPONSE = "request_response"
    SUBSCRIBE_NOTIFY = "subscribe_notify"


# ---------------------------------------------------------------------------
# ServiceDescriptor — the immutable identity card of one service
# (08-services.md §5)
# ---------------------------------------------------------------------------
class ServiceDescriptor(BaseModel):
    """
    Complete metadata for one registered SEL service.

    Fields:
      name         : dotted name '{nf}.{domain}.{action}' (unique key)
      kind         : read | action | control
      pattern      : request_response | subscribe_notify
      owner_nf     : the NFType value string that handles this service
      policy_tags  : labels the Policy Engine matches on (e.g. 'mutates:nrf')
      spec_ref     : 3GPP TS/TR clause approximated
      approx_op    : real SBA operation (e.g. 'Nnrf_NFDiscovery_Request')
      idempotent   : True = safe to retry as-is
      compensation : inverse service name (for Recovery rollback) or None
      description  : human/agent-facing summary
    """

    model_config = {"frozen": True}

    name: str = Field(..., description="'{nf}.{domain}.{action}'")
    kind: ServiceKind
    pattern: Pattern = Pattern.REQUEST_RESPONSE
    owner_nf: str = Field(..., description="NFType value, e.g. 'NRF'")

    policy_tags: tuple[str, ...] = Field(default=())
    spec_ref: str = Field(default="", description="3GPP TS/TR clause")
    approximates_operation: str = Field(default="", description="Real SBA op")

    idempotent: bool = True
    compensation: str | None = None   # inverse service for rollback

    description: str = ""

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def nf_prefix(self) -> str:
        """First segment of the name, e.g. 'nrf' from 'nrf.discover'."""
        return self.name.split(".")[0]

    def requires_policy_check(self) -> bool:
        return self.kind == ServiceKind.ACTION

    def has_tag(self, tag: str) -> bool:
        return tag in self.policy_tags

    def to_tool_schema(self) -> dict[str, Any]:
        """
        Minimal JSON-schema stub for the agent Tool Adapter.
        The full schema is derived from the Pydantic input model in the SEL;
        this provides the name and description.
        """
        return {
            "name": self.name,
            "description": self.description or f"Call {self.name}",
            "kind": self.kind.value,
            "owner_nf": self.owner_nf,
        }


# ---------------------------------------------------------------------------
# ServiceResult — the outcome of one SEL invocation
# (08-services.md §7, 09-api.md §5)
# ---------------------------------------------------------------------------
class ServiceStatus(str, Enum):
    OK = "ok"
    BLOCKED = "blocked"                   # policy refused
    REQUIRES_CONFIRMATION = "requires_confirmation"  # HITL needed
    ERROR = "error"                       # unexpected failure


class ServiceResult(BaseModel):
    """
    The typed return value from the SEL Invoker.
    Returned to agents as structured tool output (not as an exception).
    """

    model_config = {"frozen": True}

    service_name: str
    status: ServiceStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    policy_id: str | None = None          # set when status=BLOCKED
    confirmation_token: str | None = None # set when status=REQUIRES_CONFIRMATION
    latency_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == ServiceStatus.OK

    @property
    def blocked(self) -> bool:
        return self.status == ServiceStatus.BLOCKED

    def to_agent_error(self) -> str:
        """Human/agent-readable description of a non-OK result."""
        if self.status == ServiceStatus.BLOCKED:
            return (
                f"POLICY_BLOCKED: service '{self.service_name}' was refused "
                f"by policy '{self.policy_id}'. {self.error or ''}"
            )
        if self.status == ServiceStatus.REQUIRES_CONFIRMATION:
            return (
                f"REQUIRES_CONFIRMATION: '{self.service_name}' needs human approval. "
                f"token={self.confirmation_token}"
            )
        return f"ERROR in '{self.service_name}': {self.error or 'unknown error'}"
