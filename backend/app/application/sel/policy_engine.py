"""
Application: Deterministic Policy Engine — PLC-1..6 predicates.

Policies are enforced by pure functions of (args, snapshot) — never by
trusting the LLM (AP4 / 05-agents.md §10).  The engine evaluates all
applicable policies in severity order (critical > high > medium > low)
and returns the first non-allow decision or ALLOW if all pass.

Predicates (condition_ref → function):
  plc1_never_zero_nrf        — block deregister if would leave zero active NRF
  plc2_healthy_target        — block deploy to FAILED/DEGRADED target
  plc3_rate_limit            — block if workflow exceeds action budget
  plc4_region_scope          — block if target region ≠ intent region
  plc5_high_impact_confirm   — require confirmation for high-impact actions
  plc6_no_op_if_stable       — block load-balance if KPIs already in bounds

Owning docs: 08-services.md §8, 05-agents.md AP4
"""
from __future__ import annotations

import logging
from typing import Any

from app.domain.services.policy import (
    BUILTIN_POLICIES,
    Policy,
    PolicyCheckResult,
    PolicyDecision,
    PolicySeverity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity ordering for evaluation (critical first)
# ---------------------------------------------------------------------------
_SEVERITY_ORDER = {
    PolicySeverity.CRITICAL: 0,
    PolicySeverity.HIGH: 1,
    PolicySeverity.MEDIUM: 2,
    PolicySeverity.LOW: 3,
}

# ---------------------------------------------------------------------------
# Predicate registry — condition_ref → pure function
# ---------------------------------------------------------------------------
PredicateFn = Any  # (args: dict, snapshot: dict | None) -> bool
_PREDICATES: dict[str, PredicateFn] = {}


def _predicate(ref: str):
    """Decorator to register a predicate under its condition_ref."""
    def decorator(fn: PredicateFn) -> PredicateFn:
        _PREDICATES[ref] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# PLC-1 — Never zero NRF
# ---------------------------------------------------------------------------
@_predicate("plc1_never_zero_nrf")
def plc1_never_zero_nrf(args: dict[str, Any], snapshot: dict | None) -> bool:
    """
    Return True (violation) when deregistering the given NF id would leave
    zero active NRF instances.
    """
    if snapshot is None:
        return False   # no snapshot → can't evaluate → allow
    nf_id: str = args.get("nf_id", "")
    nf_states: dict = snapshot.get("nf_states", {})
    # Count active NRFs excluding the one being removed
    active_nrfs = [
        nf_id_k
        for nf_id_k, state in nf_states.items()
        if state.get("type") == "NRF"
        and state.get("status") == "ACTIVE"
        and nf_id_k != nf_id
    ]
    return len(active_nrfs) == 0   # True = violation


# ---------------------------------------------------------------------------
# PLC-2 — Deploy only to healthy targets
# ---------------------------------------------------------------------------
@_predicate("plc2_healthy_target")
def plc2_healthy_target(args: dict[str, Any], snapshot: dict | None) -> bool:
    """Return True (violation) when the target NF is FAILED or DEGRADED."""
    target: str = args.get("target", "")
    if not target or snapshot is None:
        return False
    nf_states: dict = snapshot.get("nf_states", {})
    state = nf_states.get(target, {})
    return state.get("status") in ("FAILED", "DEGRADED")


# ---------------------------------------------------------------------------
# PLC-3 — Action rate limit
# ---------------------------------------------------------------------------
MAX_ACTIONS_PER_WORKFLOW = 20   # configurable

@_predicate("plc3_rate_limit")
def plc3_rate_limit(args: dict[str, Any], snapshot: dict | None) -> bool:
    """Return True (violation) when this workflow has exceeded the action budget."""
    actions_so_far: int = args.get("_actions_count", 0)
    return actions_so_far >= MAX_ACTIONS_PER_WORKFLOW


# ---------------------------------------------------------------------------
# PLC-4 — Region scoping
# ---------------------------------------------------------------------------
@_predicate("plc4_region_scope")
def plc4_region_scope(args: dict[str, Any], snapshot: dict | None) -> bool:
    """
    Return True (violation) when the action's target region does not match
    the intent's declared region scope.
    """
    intent_region: str | None = args.get("_intent_region")
    target: str = args.get("target", "")
    if not intent_region or not target or snapshot is None:
        return False
    nf_states: dict = snapshot.get("nf_states", {})
    state = nf_states.get(target, {})
    target_region: str = state.get("region", "")
    return bool(target_region) and target_region != intent_region


# ---------------------------------------------------------------------------
# PLC-5 — High-impact confirmation
# ---------------------------------------------------------------------------
@_predicate("plc5_high_impact_confirm")
def plc5_high_impact_confirm(
    args: dict[str, Any], snapshot: dict | None
) -> bool:
    """Always triggers (requires_confirmation) — matched by tag 'high-impact'."""
    return True   # tag matching already filtered; always confirm


# ---------------------------------------------------------------------------
# PLC-6 — No-op if already stable
# ---------------------------------------------------------------------------
@_predicate("plc6_no_op_if_stable")
def plc6_no_op_if_stable(args: dict[str, Any], snapshot: dict | None) -> bool:
    """
    Return True (violation/block) when the target UPF's latency KPI is
    already within its thresholds — a load-balance would be a no-op.
    """
    target: str = args.get("target", "")
    if not target or snapshot is None:
        return False
    nf_states: dict = snapshot.get("nf_states", {})
    state = nf_states.get(target, {})
    kpis = state.get("kpis", {})
    latency = kpis.get("latency_ms", {})
    # Block if latency is not currently breaching (i.e. already stable)
    return not latency.get("breaching", False)


# ---------------------------------------------------------------------------
# PolicyEngine — evaluates all applicable policies
# ---------------------------------------------------------------------------
class PolicyEngine:
    """
    Evaluates all applicable policies for a service call.
    Policies are sorted by severity (critical first); first non-allow wins.
    """

    def __init__(self, policies: list[Policy] | None = None) -> None:
        self._policies: list[Policy] = sorted(
            policies or list(BUILTIN_POLICIES),
            key=lambda p: _SEVERITY_ORDER.get(p.severity, 99),
        )

    def evaluate(
        self,
        service_name: str,
        tags: tuple[str, ...],
        args: dict[str, Any],
        snapshot: dict | None = None,
    ) -> PolicyCheckResult:
        """
        Evaluate all applicable policies in severity order.
        Returns the first non-allow result, or ALLOW if all pass.
        """
        for policy in self._policies:
            if not policy.applies_to(service_name, tags):
                continue
            predicate = _PREDICATES.get(policy.condition_ref)
            if predicate is None:
                logger.warning("No predicate for condition_ref '%s'", policy.condition_ref)
                continue
            try:
                violation = predicate(args, snapshot)
            except Exception:
                logger.exception("Predicate '%s' raised", policy.condition_ref)
                continue
            if violation:
                if policy.decision == PolicyDecision.BLOCK:
                    return PolicyCheckResult.block(policy)
                if policy.decision == PolicyDecision.REQUIRE_CONFIRMATION:
                    return PolicyCheckResult.confirm(policy)

        return PolicyCheckResult.allow()

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)
        self._policies.sort(key=lambda p: _SEVERITY_ORDER.get(p.severity, 99))

    @property
    def policy_count(self) -> int:
        return len(self._policies)
