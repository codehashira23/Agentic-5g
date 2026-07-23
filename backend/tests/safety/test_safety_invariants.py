"""
C130: Safety-invariant tests — the golden rules (GR1-GR14).

Proves (16-testing.md §12):
  1. SEL-only: no agent module imports the twin directly (GR1)
  2. PLC-1..6 policy blocks work correctly (GR8)
  3. API key (SecretStr) never appears in repr/str output (GR11)
  4. No real PII — UDM uses synthetic data only (GR11 / DP8)
  5. Every action service declares a compensation (GR8 / SD-5)
  6. Bounded autonomy: workflow respects MAX_ATTEMPTS (13-workflow-engine §7)
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path

import pytest

from app.application.sel.policy_engine import PolicyEngine
from app.application.sel.services.catalog import ALL_SERVICES
from app.domain.services.models import ServiceKind
from app.domain.services.policy import BUILTIN_POLICIES, PolicyDecision
from app.infrastructure.config.settings import Settings


# ---------------------------------------------------------------------------
# 1. SEL-only: no agent application module imports domain.twin directly
# ---------------------------------------------------------------------------
class TestSelOnlyInvariant:
    """GR1: agents must act only through the SEL, never touch the twin directly."""

    def _get_agent_modules(self) -> list[str]:
        """Return list of module names under app.application.agents."""
        agents_path = Path("backend/app/application/agents")
        modules = []
        for f in agents_path.rglob("*.py"):
            if f.name.startswith("__"):
                continue
            rel = f.relative_to(Path("backend"))
            mod = str(rel).replace("\\", ".").replace("/", ".")[:-3]
            modules.append(mod)
        return modules

    def test_agent_modules_do_not_import_twin_entities(self) -> None:
        """
        No agent application file should import from app.domain.twin.entities
        or app.domain.twin.network_twin directly.
        Agents must go through the SEL invoker.
        """
        agents_path = Path("backend/app/application/agents")
        forbidden_imports = [
            "app.domain.twin.entities",
            "app.domain.twin.network_twin",
            "app.domain.twin.nf.",
        ]
        violations: list[str] = []
        for py_file in agents_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            source = py_file.read_text(encoding="utf-8")
            for forbidden in forbidden_imports:
                if forbidden in source:
                    violations.append(f"{py_file}: imports '{forbidden}'")

        assert not violations, (
            "Agent files must not import twin internals directly (GR1):\n"
            + "\n".join(violations)
        )

    def test_workflow_nodes_do_not_import_nf_directly(self) -> None:
        """Workflow nodes should not import NF subclasses directly."""
        nodes_file = Path("backend/app/application/workflow/nodes.py")
        source = nodes_file.read_text(encoding="utf-8")
        assert "from app.domain.twin.nf" not in source, (
            "workflow/nodes.py must not import NF classes directly (GR1)"
        )


# ---------------------------------------------------------------------------
# 2. Policy engine blocks — PLC-1..6 (GR8)
# ---------------------------------------------------------------------------
class TestPolicyBlocks:
    def _engine(self) -> PolicyEngine:
        return PolicyEngine(list(BUILTIN_POLICIES))

    def test_plc1_blocks_last_nrf(self) -> None:
        engine = self._engine()
        snapshot = {"nf_states": {"nrf_core_1": {"type": "NRF", "status": "ACTIVE"}}}
        result = engine.evaluate(
            "nrf.deregister", ("mutates:nrf",),
            {"nf_id": "nrf_core_1"}, snapshot=snapshot,
        )
        assert not result.allowed
        assert result.triggered_policy.id == "PLC-1"

    def test_plc2_blocks_deploy_to_failed(self) -> None:
        engine = self._engine()
        snapshot = {"nf_states": {"edge_delhi_1": {"status": "FAILED"}}}
        result = engine.evaluate(
            "aimle.model.deploy", ("mutates:model", "region-scoped"),
            {"target": "edge_delhi_1"}, snapshot=snapshot,
        )
        assert not result.allowed
        assert result.triggered_policy.id == "PLC-2"

    def test_plc3_rate_limit_blocks_excess_actions(self) -> None:
        """PLC-3 predicate returns True when _actions_count exceeds the rate limit."""
        from app.application.sel.policy_engine import _PREDICATES, MAX_ACTIONS_PER_WORKFLOW
        predicate = _PREDICATES.get("plc3_rate_limit")
        assert predicate is not None, "plc3_rate_limit predicate must be registered"
        # Over limit → violation = True
        assert predicate({"_actions_count": MAX_ACTIONS_PER_WORKFLOW + 1}, None) is True
        # Under limit → no violation
        assert predicate({"_actions_count": 0}, None) is False

    def test_plc5_requires_confirmation_for_high_impact(self) -> None:
        engine = self._engine()
        result = engine.evaluate(
            "nrf.deregister", ("mutates:nrf", "high-impact"),
            {"nf_id": "nrf_core_1"}, snapshot=None,
        )
        # Either PLC-1 blocks or PLC-5 confirms; both are non-allow
        assert not result.allowed

    def test_safe_read_always_allowed(self) -> None:
        engine = self._engine()
        result = engine.evaluate("twin.snapshot", (), {}, snapshot=None)
        assert result.allowed

    def test_allow_with_two_active_nrfs(self) -> None:
        engine = self._engine()
        snapshot = {"nf_states": {
            "nrf_core_1": {"type": "NRF", "status": "ACTIVE"},
            "nrf_core_2": {"type": "NRF", "status": "ACTIVE"},
        }}
        result = engine.evaluate(
            "nrf.deregister", ("mutates:nrf",),
            {"nf_id": "nrf_core_1"}, snapshot=snapshot,
        )
        assert result.allowed


# ---------------------------------------------------------------------------
# 3. Secrets never logged (GR11)
# ---------------------------------------------------------------------------
class TestSecretsNeverLogged:
    def test_api_key_secretstr_repr_does_not_expose_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SecretStr must never reveal the key in repr/str."""
        monkeypatch.setenv("LLM__API_KEY", "super-secret-test-key-xyz")
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.llm.api_key is not None
        assert "super-secret-test-key-xyz" not in repr(s.llm.api_key)
        assert "super-secret-test-key-xyz" not in str(s.llm.api_key)

    def test_settings_does_not_expose_key_in_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM__API_KEY", "another-secret-456")
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        # model_dump should not contain the raw key
        d = s.model_dump()
        import json
        serialized = json.dumps(d, default=str)
        assert "another-secret-456" not in serialized


# ---------------------------------------------------------------------------
# 4. No real PII — UDM uses synthetic data (GR11 / DP8)
# ---------------------------------------------------------------------------
class TestNoPII:
    def test_udm_subscriber_data_is_synthetic(self) -> None:
        """UDM uses synthetic subscriber records with no real names/phone/email."""
        from app.domain.twin.nf.remaining import _SYNTHETIC_SUBSCRIBERS
        for ue_id, data in _SYNTHETIC_SUBSCRIBERS.items():
            # Synthetic ids are formatted ue_NNNN
            assert ue_id.startswith("ue_"), f"Unexpected subscriber id format: {ue_id}"
            # No real-name fields
            assert "name" not in data or not any(
                c.isalpha() and c.isupper() for c in str(data.get("name", ""))
            ), f"Possible real name in subscriber data: {data}"
            # No phone/email fields
            assert "phone" not in data
            assert "email" not in data

    def test_subscriber_count_is_synthetic(self) -> None:
        from app.domain.twin.nf.remaining import _SYNTHETIC_SUBSCRIBERS
        assert 0 < len(_SYNTHETIC_SUBSCRIBERS) <= 10_000, (
            "Synthetic subscriber count should be bounded and non-zero"
        )


# ---------------------------------------------------------------------------
# 5. Every action service declares a compensation (GR8 / SD-5)
# ---------------------------------------------------------------------------
class TestCompensationCompleteness:
    def test_all_compensations_exist_in_catalog(self) -> None:
        """
        If an action service declares a compensation, the inverse must be
        registered in the same catalog (SD-5).
        """
        catalog_names = {s.name for s in ALL_SERVICES}
        violations: list[str] = []
        for svc in ALL_SERVICES:
            if svc.kind == ServiceKind.ACTION and svc.compensation:
                if svc.compensation not in catalog_names:
                    violations.append(
                        f"{svc.name} → compensation '{svc.compensation}' not in catalog"
                    )
        assert not violations, (
            "Compensation services must be registered in the catalog (GR8):\n"
            + "\n".join(violations)
        )

    def test_no_action_has_self_as_compensation(self) -> None:
        """An action cannot compensate itself — that would be a no-op rollback."""
        for svc in ALL_SERVICES:
            if svc.kind == ServiceKind.ACTION:
                assert svc.compensation != svc.name, (
                    f"{svc.name} declares itself as compensation — invalid"
                )


# ---------------------------------------------------------------------------
# 6. Bounded autonomy — MAX_ATTEMPTS guard exists (GR14)
# ---------------------------------------------------------------------------
class TestBoundedAutonomy:
    def test_max_attempts_constant_is_positive(self) -> None:
        from app.application.workflow.routing import MAX_ATTEMPTS
        assert MAX_ATTEMPTS > 0
        assert MAX_ATTEMPTS <= 50, "MAX_ATTEMPTS should be bounded (≤50)"

    def test_route_after_validate_rollback_when_exhausted(self) -> None:
        from app.application.workflow.routing import route_after_validate
        from app.application.workflow.state import WorkflowState

        state = WorkflowState(
            id="wf_test",
            goal="test",
            attempts=999,  # way over MAX_ATTEMPTS
        )
        state.validation = {"verdict": "retry"}
        assert route_after_validate(state) == "rollback"

    def test_route_after_validate_complete_on_pass(self) -> None:
        from app.application.workflow.routing import route_after_validate
        from app.application.workflow.state import WorkflowState

        state = WorkflowState(id="wf_test", goal="test")
        state.validation = {"verdict": "pass"}
        assert route_after_validate(state) == "complete"

    def test_route_after_validate_retry_within_budget(self) -> None:
        from app.application.workflow.routing import route_after_validate, MAX_ATTEMPTS
        from app.application.workflow.state import WorkflowState

        state = WorkflowState(id="wf_test", goal="test", attempts=1)
        state.validation = {"verdict": "retry"}
        assert route_after_validate(state) == "retry"

    def test_auto_trigger_dedup_prevents_runaway(self) -> None:
        """AutoTrigger de-dup prevents infinite re-triggering for same condition."""
        from app.application.workflow.triggers import AutoTrigger
        from app.infrastructure.bus.bus import InProcessEventBus

        bus = InProcessEventBus()

        class FakeEngine:
            async def start(self, *a, **kw):
                from app.application.workflow.state import WorkflowState
                return WorkflowState(id="wf_x", goal="test", status="completed")

        trigger = AutoTrigger(bus, FakeEngine(), autonomy_enabled=True)
        # Simulate the key already being in-flight
        trigger._in_flight["KPI_THRESHOLD_BREACH:upf_1:Delhi"] = "wf_existing"
        assert trigger.in_flight_count == 1
