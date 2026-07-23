"""
C048: Unit tests for ServiceDescriptor, ServiceResult, Policy, PolicyCheckResult,
and the BUILTIN_POLICIES tuple.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.services.models import (
    Pattern,
    ServiceDescriptor,
    ServiceKind,
    ServiceResult,
    ServiceStatus,
)
from app.domain.services.policy import (
    BUILTIN_POLICIES,
    Policy,
    PolicyCheckResult,
    PolicyDecision,
    PolicySeverity,
)


# ---------------------------------------------------------------------------
# ServiceDescriptor
# ---------------------------------------------------------------------------
class TestServiceDescriptor:
    def _make(self, **kw) -> ServiceDescriptor:
        defaults = dict(
            name="nrf.discover",
            kind=ServiceKind.READ,
            owner_nf="NRF",
            description="Discover NFs by type/region",
        )
        defaults.update(kw)
        return ServiceDescriptor(**defaults)

    def test_construction(self) -> None:
        sd = self._make()
        assert sd.name == "nrf.discover"
        assert sd.kind == ServiceKind.READ
        assert sd.owner_nf == "NRF"

    def test_immutable(self) -> None:
        sd = self._make()
        with pytest.raises(ValidationError):
            sd.name = "changed"  # type: ignore[misc]

    def test_nf_prefix(self) -> None:
        sd = self._make(name="nwdaf.analytics.congestion.subscribe")
        assert sd.nf_prefix == "nwdaf"

    def test_requires_policy_check_read(self) -> None:
        sd = self._make(kind=ServiceKind.READ)
        assert sd.requires_policy_check() is False

    def test_requires_policy_check_action(self) -> None:
        sd = self._make(kind=ServiceKind.ACTION)
        assert sd.requires_policy_check() is True

    def test_requires_policy_check_control(self) -> None:
        sd = self._make(kind=ServiceKind.CONTROL)
        assert sd.requires_policy_check() is False

    def test_has_tag_true(self) -> None:
        sd = self._make(policy_tags=("mutates:nrf", "high-impact"))
        assert sd.has_tag("mutates:nrf") is True

    def test_has_tag_false(self) -> None:
        sd = self._make(policy_tags=("mutates:nrf",))
        assert sd.has_tag("region-scoped") is False

    def test_default_tags_empty(self) -> None:
        sd = self._make()
        assert sd.policy_tags == ()

    def test_idempotent_default_true(self) -> None:
        sd = self._make()
        assert sd.idempotent is True

    def test_compensation_default_none(self) -> None:
        sd = self._make()
        assert sd.compensation is None

    def test_compensation_set(self) -> None:
        sd = self._make(
            name="aimle.model.deploy",
            kind=ServiceKind.ACTION,
            owner_nf="NWDAF",
            compensation="aimle.model.retire",
        )
        assert sd.compensation == "aimle.model.retire"

    def test_to_tool_schema(self) -> None:
        sd = self._make()
        schema = sd.to_tool_schema()
        assert schema["name"] == "nrf.discover"
        assert "description" in schema
        assert schema["kind"] == "read"
        assert schema["owner_nf"] == "NRF"

    def test_spec_ref_and_approx_op(self) -> None:
        sd = self._make(
            spec_ref="TS 23.501 §6.2.6",
            approximates_operation="Nnrf_NFDiscovery_Request",
        )
        assert "23.501" in sd.spec_ref
        assert "NFDiscovery" in sd.approximates_operation

    def test_subscribe_notify_pattern(self) -> None:
        sd = self._make(
            name="nwdaf.analytics.congestion.subscribe",
            kind=ServiceKind.ACTION,
            owner_nf="NWDAF",
            pattern=Pattern.SUBSCRIBE_NOTIFY,
        )
        assert sd.pattern == Pattern.SUBSCRIBE_NOTIFY


# ---------------------------------------------------------------------------
# ServiceResult
# ---------------------------------------------------------------------------
class TestServiceResult:
    def test_ok_result(self) -> None:
        r = ServiceResult(
            service_name="nrf.discover",
            status=ServiceStatus.OK,
            output={"profiles": [], "count": 0},
        )
        assert r.ok is True
        assert r.blocked is False

    def test_blocked_result(self) -> None:
        r = ServiceResult(
            service_name="nrf.deregister",
            status=ServiceStatus.BLOCKED,
            policy_id="PLC-1",
            error="Would leave zero NRF",
        )
        assert r.blocked is True
        assert r.ok is False

    def test_requires_confirmation_result(self) -> None:
        r = ServiceResult(
            service_name="bulk.deregister",
            status=ServiceStatus.REQUIRES_CONFIRMATION,
            confirmation_token="tok_abc",
        )
        assert r.status == ServiceStatus.REQUIRES_CONFIRMATION

    def test_error_result(self) -> None:
        r = ServiceResult(
            service_name="nrf.discover",
            status=ServiceStatus.ERROR,
            error="NRF is FAILED",
        )
        assert r.ok is False

    def test_to_agent_error_blocked(self) -> None:
        r = ServiceResult(
            service_name="nrf.deregister",
            status=ServiceStatus.BLOCKED,
            policy_id="PLC-1",
            error="zero NRF",
        )
        msg = r.to_agent_error()
        assert "POLICY_BLOCKED" in msg
        assert "PLC-1" in msg
        assert "nrf.deregister" in msg

    def test_to_agent_error_confirm(self) -> None:
        r = ServiceResult(
            service_name="bulk.op",
            status=ServiceStatus.REQUIRES_CONFIRMATION,
            confirmation_token="tok_xyz",
        )
        msg = r.to_agent_error()
        assert "REQUIRES_CONFIRMATION" in msg
        assert "tok_xyz" in msg

    def test_to_agent_error_generic(self) -> None:
        r = ServiceResult(
            service_name="nrf.discover",
            status=ServiceStatus.ERROR,
            error="internal failure",
        )
        msg = r.to_agent_error()
        assert "ERROR" in msg
        assert "internal failure" in msg

    def test_immutable(self) -> None:
        r = ServiceResult(
            service_name="x", status=ServiceStatus.OK
        )
        with pytest.raises(ValidationError):
            r.status = ServiceStatus.ERROR  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------
class TestPolicy:
    def _make(self, **kw) -> Policy:
        defaults = dict(
            id="TEST-1",
            name="Test policy",
            decision=PolicyDecision.BLOCK,
            condition_ref="test_predicate",
        )
        defaults.update(kw)
        return Policy(**defaults)

    def test_construction(self) -> None:
        p = self._make()
        assert p.id == "TEST-1"
        assert p.enabled is True
        assert p.builtin is False

    def test_immutable(self) -> None:
        p = self._make()
        with pytest.raises(ValidationError):
            p.enabled = False  # type: ignore[misc]

    def test_with_enabled_returns_new_policy(self) -> None:
        p = self._make()
        p2 = p.with_enabled(False)
        assert p.enabled is True   # original unchanged
        assert p2.enabled is False

    def test_applies_to_disabled_policy(self) -> None:
        p = self._make(enabled=False)
        assert p.applies_to("nrf.deregister", ()) is False

    def test_applies_to_by_service(self) -> None:
        p = self._make(match_services=("nrf.deregister",))
        assert p.applies_to("nrf.deregister", ()) is True
        assert p.applies_to("nrf.discover", ()) is False

    def test_applies_to_by_tag(self) -> None:
        p = self._make(match_tags=("mutates:nrf",))
        assert p.applies_to("any.service", ("mutates:nrf",)) is True
        assert p.applies_to("any.service", ("region-scoped",)) is False

    def test_applies_to_no_filters_matches_all(self) -> None:
        p = self._make()  # no match_services, no match_tags
        assert p.applies_to("anything", ()) is True

    def test_applies_to_service_and_tag_must_both_match(self) -> None:
        p = self._make(
            match_services=("nrf.deregister",),
            match_tags=("mutates:nrf",),
        )
        # correct service but wrong tag
        assert p.applies_to("nrf.deregister", ("region-scoped",)) is False
        # correct service and correct tag
        assert p.applies_to("nrf.deregister", ("mutates:nrf",)) is True


# ---------------------------------------------------------------------------
# PolicyCheckResult
# ---------------------------------------------------------------------------
class TestPolicyCheckResult:
    def _policy(self) -> Policy:
        return Policy(
            id="PLC-1",
            name="Never zero NRF",
            decision=PolicyDecision.BLOCK,
            condition_ref="plc1_never_zero_nrf",
            message="Would leave zero NRF",
        )

    def test_allow(self) -> None:
        r = PolicyCheckResult.allow()
        assert r.allowed is True
        assert r.decision == PolicyDecision.ALLOW
        assert r.triggered_policy is None

    def test_block(self) -> None:
        r = PolicyCheckResult.block(self._policy())
        assert r.allowed is False
        assert r.decision == PolicyDecision.BLOCK
        assert r.triggered_policy is not None
        assert "zero NRF" in r.message

    def test_confirm(self) -> None:
        p = Policy(
            id="PLC-5",
            name="High-impact",
            decision=PolicyDecision.REQUIRE_CONFIRMATION,
            condition_ref="plc5_high_impact_confirm",
            message="Needs approval",
        )
        r = PolicyCheckResult.confirm(p)
        assert r.decision == PolicyDecision.REQUIRE_CONFIRMATION
        assert r.triggered_policy is not None

    def test_immutable(self) -> None:
        r = PolicyCheckResult.allow()
        with pytest.raises(ValidationError):
            r.decision = PolicyDecision.BLOCK  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BUILTIN_POLICIES
# ---------------------------------------------------------------------------
class TestBuiltinPolicies:
    def test_six_builtin_policies(self) -> None:
        assert len(BUILTIN_POLICIES) == 6

    def test_all_have_builtin_true(self) -> None:
        for p in BUILTIN_POLICIES:
            assert p.builtin is True, f"{p.id} should have builtin=True"

    def test_all_have_condition_refs(self) -> None:
        for p in BUILTIN_POLICIES:
            assert p.condition_ref, f"{p.id} missing condition_ref"

    def test_plc1_is_critical(self) -> None:
        plc1 = next(p for p in BUILTIN_POLICIES if p.id == "PLC-1")
        assert plc1.severity == PolicySeverity.CRITICAL

    def test_plc5_requires_confirmation(self) -> None:
        plc5 = next(p for p in BUILTIN_POLICIES if p.id == "PLC-5")
        assert plc5.decision == PolicyDecision.REQUIRE_CONFIRMATION

    def test_plc1_applies_to_nrf_deregister(self) -> None:
        plc1 = next(p for p in BUILTIN_POLICIES if p.id == "PLC-1")
        assert plc1.applies_to("nrf.deregister", ("mutates:nrf",)) is True

    def test_plc2_applies_to_model_deploy(self) -> None:
        plc2 = next(p for p in BUILTIN_POLICIES if p.id == "PLC-2")
        assert plc2.applies_to("aimle.model.deploy", ("mutates:model",)) is True

    def test_all_ids_unique(self) -> None:
        ids = [p.id for p in BUILTIN_POLICIES]
        assert len(ids) == len(set(ids))
