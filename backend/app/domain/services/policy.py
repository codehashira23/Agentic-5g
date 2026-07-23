"""
Domain: Policy — the guardrail model for the SEL Policy Engine.

Defines:
  - PolicyDecision : allow | block | require_confirmation
  - Policy         : one guardrail rule (stored in DB, evaluated in SEL)

Rules:
  - Pure Python + Pydantic only. Zero framework imports.
  - Policy logic (predicates) lives in the APPLICATION layer
    (application/sel/policy_engine.py).  This module contains only the
    DATA MODEL — what a policy looks like and what decisions it produces.
  - Policies are immutable value objects; editing creates a new instance.

Owning docs: 08-services.md §8, 15-kiro-rules.md GR8
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# PolicyDecision — the three possible outcomes of a policy check
# ---------------------------------------------------------------------------
class PolicyDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_CONFIRMATION = "require_confirmation"


# ---------------------------------------------------------------------------
# PolicySeverity — how critical the policy is
# ---------------------------------------------------------------------------
class PolicySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Policy — one guardrail rule
# (08-services.md §8, built-ins PLC-1..6)
# ---------------------------------------------------------------------------
class Policy(BaseModel):
    """
    A single guardrail policy.

    The `condition_ref` field maps to a pure function in the application
    layer (policy_engine.py).  This domain model stores the *configuration*
    — id, name, enabled, severity, match criteria, and decision.

    Built-in policies (PLC-1..6) have `builtin=True` and cannot be deleted;
    they can only be disabled via `enabled=False`.
    """

    model_config = {"frozen": True}

    id: str = Field(
        ...,
        description="Stable identifier, e.g. 'PLC-1'",
    )
    name: str
    enabled: bool = True
    severity: PolicySeverity = PolicySeverity.HIGH
    builtin: bool = False     # True for PLC-1..6; cannot delete, only disable

    # Match criteria — which services / tags this policy applies to
    match_services: tuple[str, ...] = Field(
        default=(),
        description="Exact service names this policy applies to (empty = any)",
    )
    match_tags: tuple[str, ...] = Field(
        default=(),
        description="Policy tags that trigger this policy (e.g. 'mutates:nrf')",
    )

    # The decision this policy produces when its condition is met
    decision: PolicyDecision = PolicyDecision.BLOCK

    # Reference to the predicate function in policy_engine.py
    condition_ref: str = Field(
        ...,
        description="Name of the pure predicate function in policy_engine.py",
    )

    # Human-readable explanation (shown in Agent Console + Logs)
    message: str = ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def matches_service(self, service_name: str) -> bool:
        """True if this policy applies to the given service name."""
        if self.match_services and service_name not in self.match_services:
            return False
        return True

    def matches_tags(self, tags: tuple[str, ...]) -> bool:
        """True if any of this policy's match_tags appears in tags."""
        if not self.match_tags:
            return True  # no tag filter → match all
        return bool(set(self.match_tags) & set(tags))

    def applies_to(self, service_name: str, tags: tuple[str, ...]) -> bool:
        """True if this policy should be evaluated for this call."""
        if not self.enabled:
            return False
        return self.matches_service(service_name) and self.matches_tags(tags)

    def with_enabled(self, enabled: bool) -> Policy:
        """Return a new Policy with updated enabled flag (immutable update)."""
        return self.model_copy(update={"enabled": enabled})


# ---------------------------------------------------------------------------
# PolicyCheckResult — the outcome of evaluating all applicable policies
# ---------------------------------------------------------------------------
class PolicyCheckResult(BaseModel):
    """
    The aggregated result of running all applicable policies against a call.
    Produced by the Policy Engine; consumed by the Invoker.
    """

    model_config = {"frozen": True}

    decision: PolicyDecision
    triggered_policy: Policy | None = None
    message: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == PolicyDecision.ALLOW

    @classmethod
    def allow(cls) -> PolicyCheckResult:
        return cls(decision=PolicyDecision.ALLOW, message="")

    @classmethod
    def block(cls, policy: Policy) -> PolicyCheckResult:
        return cls(
            decision=PolicyDecision.BLOCK,
            triggered_policy=policy,
            message=policy.message,
        )

    @classmethod
    def confirm(cls, policy: Policy) -> PolicyCheckResult:
        return cls(
            decision=PolicyDecision.REQUIRE_CONFIRMATION,
            triggered_policy=policy,
            message=policy.message,
        )


# ---------------------------------------------------------------------------
# Built-in policy definitions (PLC-1..6)
# The actual predicate logic lives in application/sel/policy_engine.py.
# These are the DATA objects stored in the DB and seeded at startup.
# ---------------------------------------------------------------------------
BUILTIN_POLICIES: tuple[Policy, ...] = (
    Policy(
        id="PLC-1",
        name="Never zero NRF",
        severity=PolicySeverity.CRITICAL,
        builtin=True,
        match_services=("nrf.deregister",),
        match_tags=("mutates:nrf",),
        decision=PolicyDecision.BLOCK,
        condition_ref="plc1_never_zero_nrf",
        message="Deregistering this NRF would leave zero active NRF instances.",
    ),
    Policy(
        id="PLC-2",
        name="Deploy only to healthy targets",
        severity=PolicySeverity.HIGH,
        builtin=True,
        match_services=("aimle.model.deploy",),
        match_tags=("mutates:model",),
        decision=PolicyDecision.BLOCK,
        condition_ref="plc2_healthy_target",
        message="Cannot deploy a model to a FAILED or DEGRADED target.",
    ),
    Policy(
        id="PLC-3",
        name="Action rate limit",
        severity=PolicySeverity.MEDIUM,
        builtin=True,
        match_tags=("action",),
        decision=PolicyDecision.BLOCK,
        condition_ref="plc3_rate_limit",
        message="This workflow has exceeded the maximum allowed action count.",
    ),
    Policy(
        id="PLC-4",
        name="Region scoping",
        severity=PolicySeverity.HIGH,
        builtin=True,
        match_tags=("region-scoped",),
        decision=PolicyDecision.BLOCK,
        condition_ref="plc4_region_scope",
        message="Action target region does not match the intent's region scope.",
    ),
    Policy(
        id="PLC-5",
        name="High-impact confirmation",
        severity=PolicySeverity.CRITICAL,
        builtin=True,
        match_tags=("high-impact",),
        decision=PolicyDecision.REQUIRE_CONFIRMATION,
        condition_ref="plc5_high_impact_confirm",
        message="This action has high impact and requires human confirmation.",
    ),
    Policy(
        id="PLC-6",
        name="No-op if already stable",
        severity=PolicySeverity.LOW,
        builtin=True,
        match_tags=("mutates:userplane",),
        decision=PolicyDecision.BLOCK,
        condition_ref="plc6_no_op_if_stable",
        message="KPIs are already within bounds; this action would be a no-op.",
    ),
)
