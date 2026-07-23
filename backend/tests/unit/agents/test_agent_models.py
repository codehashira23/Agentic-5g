"""
C049: Unit tests for agent structured I/O models and memory value objects.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.domain.agents.memory import KnowledgeEdge, KnowledgeNode, MemoryRecord
from app.domain.agents.models import (
    AgentRole,
    Compensation,
    CompensationResult,
    CriterionResult,
    Interpretation,
    KGDelta,
    KnowledgeDelta,
    MemoryScope,
    MemoryWrite,
    Observation,
    OptimizationOption,
    OptimizationProposal,
    Plan,
    RecoveryPlan,
    RetrievalResult,
    Step,
    StepResult,
    Validation,
    ValidationVerdict,
    WorkflowSummary,
)


# ---------------------------------------------------------------------------
# AgentRole enum
# ---------------------------------------------------------------------------
class TestAgentRole:
    def test_all_seven_roles(self) -> None:
        roles = {r.value for r in AgentRole}
        assert roles == {
            "planner", "executor", "observer",
            "optimizer", "recovery", "documentation", "memory",
        }


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------
class TestObservation:
    def test_construction(self) -> None:
        o = Observation(
            rationale="Observed twin at tick 5.",
            tick=5,
            health_pct=0.9,
        )
        assert o.tick == 5
        assert o.health_pct == 0.9

    def test_rationale_required(self) -> None:
        with pytest.raises(ValidationError):
            Observation(tick=1, health_pct=1.0)  # type: ignore[call-arg]

    def test_health_pct_bounds(self) -> None:
        with pytest.raises(ValidationError):
            Observation(rationale="x", tick=1, health_pct=1.5)

    def test_defaults(self) -> None:
        o = Observation(rationale="ok", tick=0, health_pct=1.0)
        assert o.active_workflows == 0
        assert o.entity_states == {}
        assert o.notable_events == []
        assert o.memory_summary == ""

    def test_immutable(self) -> None:
        o = Observation(rationale="x", tick=1, health_pct=1.0)
        with pytest.raises(ValidationError):
            o.tick = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class TestValidation:
    def test_pass_verdict(self) -> None:
        v = Validation(
            rationale="Both criteria met.",
            verdict=ValidationVerdict.PASS,
            criteria=[
                CriterionResult(criterion="model deployed", met=True,
                                evidence="state=deployed"),
            ],
        )
        assert v.verdict == ValidationVerdict.PASS

    def test_retry_verdict(self) -> None:
        v = Validation(rationale="Partial.", verdict=ValidationVerdict.RETRY)
        assert v.verdict == ValidationVerdict.RETRY

    def test_fail_verdict(self) -> None:
        v = Validation(rationale="NRF gone.", verdict=ValidationVerdict.FAIL)
        assert v.verdict == ValidationVerdict.FAIL

    def test_criterion_result(self) -> None:
        cr = CriterionResult(criterion="latency < 20ms", met=False,
                             evidence="latency=25ms")
        assert cr.met is False
        assert "25ms" in cr.evidence


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------
class TestInterpretation:
    def test_construction(self) -> None:
        i = Interpretation(
            rationale="Deploy a model to Delhi Edge.",
            objective="Reduce congestion in Delhi",
            targets=["edge_delhi_1"],
            constraints=["PLC-4: Delhi only"],
            success_criteria=["model deployed", "subscription active"],
        )
        assert i.objective == "Reduce congestion in Delhi"
        assert len(i.targets) == 1
        assert len(i.success_criteria) == 2


# ---------------------------------------------------------------------------
# Step and Plan
# ---------------------------------------------------------------------------
class TestStep:
    def test_construction(self) -> None:
        s = Step(index=0, service="nrf.discover", args={"nf_type": "Edge"})
        assert s.index == 0
        assert s.service == "nrf.discover"

    def test_index_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            Step(index=-1, service="nrf.discover")

    def test_immutable(self) -> None:
        s = Step(index=0, service="x")
        with pytest.raises(ValidationError):
            s.service = "y"  # type: ignore[misc]


class TestPlan:
    def _three_step_plan(self) -> Plan:
        return Plan(
            rationale="Three steps needed.",
            steps=[
                Step(index=0, service="nrf.discover"),
                Step(index=1, service="aimle.model.deploy", depends_on=[0]),
                Step(index=2, service="nwdaf.analytics.congestion.subscribe",
                     depends_on=[1]),
            ],
            success_criteria=["model deployed", "subscription active"],
        )

    def test_step_count(self) -> None:
        plan = self._three_step_plan()
        assert plan.step_count() == 3

    def test_no_cycles_in_valid_plan(self) -> None:
        plan = self._three_step_plan()
        assert plan.has_cycles() is False

    def test_all_services_in_catalog(self) -> None:
        plan = self._three_step_plan()
        catalog = {
            "nrf.discover",
            "aimle.model.deploy",
            "nwdaf.analytics.congestion.subscribe",
        }
        assert plan.all_services_in_catalog(catalog) is True

    def test_missing_service_not_in_catalog(self) -> None:
        plan = self._three_step_plan()
        assert plan.all_services_in_catalog({"nrf.discover"}) is False

    def test_empty_plan(self) -> None:
        plan = Plan(rationale="nothing to do", steps=[])
        assert plan.step_count() == 0
        assert plan.has_cycles() is False


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------
class TestStepResult:
    def test_ok_result(self) -> None:
        r = StepResult(
            rationale="Model deployed.",
            step_index=1,
            service="aimle.model.deploy",
            status="ok",
            result={"state": "deployed"},
            success_met=True,
            compensation=Compensation(
                service="aimle.model.retire",
                args={"model_id": "m1"},
                step_index=1,
            ),
        )
        assert r.status == "ok"
        assert r.success_met is True
        assert r.compensation is not None
        assert r.compensation.service == "aimle.model.retire"

    def test_failed_result_no_compensation(self) -> None:
        r = StepResult(
            rationale="NRF failed.",
            step_index=0,
            service="nrf.discover",
            status="failed",
            success_met=False,
        )
        assert r.compensation is None

    def test_blocked_result_with_hint(self) -> None:
        r = StepResult(
            rationale="Blocked.",
            step_index=2,
            service="aimle.model.deploy",
            status="blocked",
            success_met=False,
            retry_hint={"target": "edge_mumbai_1"},
        )
        assert r.retry_hint is not None


# ---------------------------------------------------------------------------
# OptimizationProposal
# ---------------------------------------------------------------------------
class TestOptimizationProposal:
    def test_best_option(self) -> None:
        p = OptimizationProposal(
            rationale="Two options.",
            objective="reduce latency",
            options=[
                OptimizationOption(rank=2, actions=[], expected_impact="medium"),
                OptimizationOption(rank=1, actions=[], expected_impact="high"),
            ],
        )
        best = p.best_option()
        assert best is not None
        assert best.rank == 1

    def test_best_option_empty(self) -> None:
        p = OptimizationProposal(rationale="x", objective="y", options=[])
        assert p.best_option() is None


# ---------------------------------------------------------------------------
# RecoveryPlan
# ---------------------------------------------------------------------------
class TestRecoveryPlan:
    def test_construction(self) -> None:
        rp = RecoveryPlan(
            rationale="Reversing 2 steps.",
            steps=[
                Compensation(service="aimle.model.retire",
                             args={"model_id": "m1"}, step_index=1),
                Compensation(service="nwdaf.analytics.unsubscribe",
                             args={"subscription_id": "sub_1"}, step_index=2),
            ],
        )
        assert len(rp.steps) == 2
        assert rp.escalate is False

    def test_escalation(self) -> None:
        rp = RecoveryPlan(
            rationale="Compensation blocked.",
            steps=[],
            escalate=True,
            escalate_reason="PLC-1 prevents rollback",
        )
        assert rp.escalate is True
        assert "PLC-1" in rp.escalate_reason


# ---------------------------------------------------------------------------
# WorkflowSummary
# ---------------------------------------------------------------------------
class TestWorkflowSummary:
    def test_construction(self) -> None:
        ws = WorkflowSummary(
            rationale="Workflow done.",
            workflow_id="wf_abc",
            goal="Deploy model to Delhi",
            outcome="success",
            narrative="Deployed congestion model to edge_delhi_1.",
            evidence=["model state=deployed", "subscription active"],
            lessons=["Delhi Edge deploys reliably"],
            kg_deltas=[
                KGDelta(src="model:congestion-det",
                        relation="hosted_on",
                        dst="nf:edge_delhi_1"),
            ],
        )
        assert ws.outcome == "success"
        assert len(ws.kg_deltas) == 1
        assert ws.kg_deltas[0].relation == "hosted_on"


# ---------------------------------------------------------------------------
# MemoryWrite and KnowledgeDelta
# ---------------------------------------------------------------------------
class TestMemoryWrite:
    def test_episodic(self) -> None:
        mw = MemoryWrite(
            scope=MemoryScope.EPISODIC,
            content={"goal": "deploy model", "outcome": "success"},
            summary="Deployed congestion model to Delhi Edge",
            provenance_workflow_id="wf_abc",
        )
        assert mw.scope == MemoryScope.EPISODIC
        assert "wf_abc" == mw.provenance_workflow_id

    def test_semantic(self) -> None:
        mw = MemoryWrite(
            scope=MemoryScope.SEMANTIC,
            content={"fact": "Delhi Edge congests at 18:00-21:00"},
            summary="Delhi peak congestion window",
        )
        assert mw.scope == MemoryScope.SEMANTIC


class TestKnowledgeDelta:
    def test_upserts(self) -> None:
        kd = KnowledgeDelta(upserts=[
            KGDelta(src="nf:upf_delhi_1", relation="caused_by",
                    dst="incident:inc_001"),
        ])
        assert len(kd.upserts) == 1


# ---------------------------------------------------------------------------
# RetrievalResult
# ---------------------------------------------------------------------------
class TestRetrievalResult:
    def test_defaults(self) -> None:
        r = RetrievalResult(rationale="No relevant memories found.")
        assert r.episodic == []
        assert r.semantic == []
        assert r.kg_neighbourhood == {}

    def test_with_data(self) -> None:
        r = RetrievalResult(
            rationale="Found 1 episodic memory.",
            episodic=[{"summary": "Last deploy succeeded"}],
            semantic=[{"fact": "Delhi peak at 18:00"}],
        )
        assert len(r.episodic) == 1
        assert len(r.semantic) == 1


# ---------------------------------------------------------------------------
# MemoryRecord
# ---------------------------------------------------------------------------
class TestMemoryRecord:
    def _make(self, **kw) -> MemoryRecord:
        defaults = dict(
            id="mem_001",
            scope=MemoryScope.EPISODIC,
            content={"goal": "test"},
            summary="Test memory",
        )
        defaults.update(kw)
        return MemoryRecord(**defaults)

    def test_construction(self) -> None:
        mr = self._make()
        assert mr.id == "mem_001"
        assert mr.scope == MemoryScope.EPISODIC
        assert mr.weight == 1.0

    def test_not_expired_when_no_expiry(self) -> None:
        mr = self._make()
        assert mr.is_expired() is False

    def test_expired_when_past_expiry(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        mr = self._make(expires_at=past)
        assert mr.is_expired() is True

    def test_not_expired_when_future_expiry(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        mr = self._make(expires_at=future)
        assert mr.is_expired() is False

    def test_decay_reduces_weight(self) -> None:
        mr = self._make(scope=MemoryScope.SEMANTIC)
        mr2 = mr.decay(factor=0.9)
        assert mr.weight == 1.0       # original unchanged
        assert abs(mr2.weight - 0.9) < 1e-9

    def test_decay_floor_at_zero(self) -> None:
        mr = self._make(weight=0.01, scope=MemoryScope.SEMANTIC)
        mr2 = mr.decay(factor=0.0)
        assert mr2.weight == 0.0

    def test_immutable(self) -> None:
        mr = self._make()
        with pytest.raises(ValidationError):
            mr.weight = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# KnowledgeNode and KnowledgeEdge
# ---------------------------------------------------------------------------
class TestKnowledgeNode:
    def test_construction(self) -> None:
        n = KnowledgeNode(
            id="nf:upf_delhi_1",
            entity_type="nf",
            label="UPF Delhi 1",
        )
        assert n.id == "nf:upf_delhi_1"
        assert n.props == {}

    def test_with_props(self) -> None:
        n = KnowledgeNode(id="nf:upf_1", entity_type="nf", label="UPF 1")
        n2 = n.with_props(region="Delhi", status="ACTIVE")
        assert n.props == {}              # original unchanged
        assert n2.props["region"] == "Delhi"

    def test_with_props_merges(self) -> None:
        n = KnowledgeNode(id="x", entity_type="nf", label="x",
                          props={"a": 1})
        n2 = n.with_props(b=2)
        assert n2.props == {"a": 1, "b": 2}

    def test_immutable(self) -> None:
        n = KnowledgeNode(id="x", entity_type="nf", label="x")
        with pytest.raises(ValidationError):
            n.label = "y"  # type: ignore[misc]


class TestKnowledgeEdge:
    def test_construction(self) -> None:
        e = KnowledgeEdge(
            src_id="model:congestion-det",
            relation="hosted_on",
            dst_id="nf:edge_delhi_1",
            provenance_workflow_id="wf_abc",
        )
        assert e.relation == "hosted_on"
        assert e.provenance_workflow_id == "wf_abc"

    def test_key_tuple(self) -> None:
        e = KnowledgeEdge(src_id="a", relation="caused_by", dst_id="b")
        assert e.key == ("a", "caused_by", "b")

    def test_immutable(self) -> None:
        e = KnowledgeEdge(src_id="a", relation="r", dst_id="b")
        with pytest.raises(ValidationError):
            e.relation = "changed"  # type: ignore[misc]
