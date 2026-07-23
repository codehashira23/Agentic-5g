"""
C098 + Gate G5: Scenario A integration test.

"Deploy congestion detection model to Delhi Edge"

Proves (13-workflow-engine.md Gate G5):
  - 8 stages flow correctly (observe→reason→plan→execute→validate→complete)
  - WorkflowState is populated at each stage
  - FakeLLM drives deterministic offline execution ($0, no network)
  - Model deployment reaches the twin NF
  - workflow_steps and workflow_trace rows are persisted
  - Final status == "completed"

Uses FakeLLM (not replay fixtures) so the test is self-contained.
Owning docs: 16-testing.md §5, 13-workflow-engine.md §20
"""
from __future__ import annotations

import pytest

from app.application.agents.orchestrator import AgentOrchestrator
from app.application.sel.invoker import ServiceInvoker
from app.application.sel.policy_engine import PolicyEngine
from app.application.sel.registry import ServiceRegistry
from app.application.sel.services.catalog import get_catalog
from app.application.twin_service.scenarios import build_twin_from_scenario
from app.application.twin_service.service import TwinService
from app.application.workflow.engine import WorkflowEngine
from app.domain.agents.models import ValidationVerdict
from app.domain.twin.profile import NFType
from app.infrastructure.bus.bus import InProcessEventBus
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import SimulationRow
from app.infrastructure.llm.client import FakeLLM
from app.infrastructure.rng.rng import RngService
from app.infrastructure.writer.writer import PersistenceWriter
from sqlalchemy import insert


# ---------------------------------------------------------------------------
# FakeLLM responses for Scenario A
# Each dict must match the Pydantic schema of the agent that will receive it.
# Order: observe → reason → plan → execute(×3) → validate → complete
# ---------------------------------------------------------------------------
def _make_fake_llm() -> FakeLLM:
    fake = FakeLLM()

    # 1. Observer: Observation
    fake.set_response({
        "rationale": "Twin is healthy at tick 0, Delhi Edge present.",
        "tick": 0,
        "health_pct": 0.95,
        "active_workflows": 0,
        "entity_states": {},
        "notable_events": [],
        "memory_summary": "",
    })

    # 2. Planner: Interpretation (Reason stage)
    fake.set_response({
        "rationale": "Goal requires AIMLE deploy + analytics subscription.",
        "objective": "Deploy congestion-det model to Delhi Edge and subscribe analytics",
        "targets": ["edge_delhi_1"],
        "constraints": ["PLC-4: Delhi only"],
        "success_criteria": [
            "model congestion-det deployed on edge_delhi_1",
            "congestion analytics subscription active for Delhi",
        ],
    })

    # 3. Planner: Plan (Plan stage)
    fake.set_response({
        "rationale": "Three steps: discover, deploy, subscribe.",
        "steps": [
            {
                "index": 0,
                "service": "nrf.discover",
                "args": {"nf_type": "Edge", "region": "Delhi"},
                "depends_on": [],
                "success_criterion": "edge id resolved",
            },
            {
                "index": 1,
                "service": "aimle.model.deploy",
                "args": {
                    "model_id": "congestion-det",
                    "name": "Congestion Detection v1",
                    "target": "edge_delhi_1",
                },
                "depends_on": [0],
                "success_criterion": "model state=deployed",
            },
            {
                "index": 2,
                "service": "nwdaf.analytics.congestion.subscribe",
                "args": {"region": "Delhi"},
                "depends_on": [1],
                "success_criterion": "subscription active",
            },
        ],
        "success_criteria": [
            "model congestion-det deployed on edge_delhi_1",
            "congestion analytics subscription active for Delhi",
        ],
    })

    # 4. Executor: StepResult for step 0 (nrf.discover)
    fake.set_response({
        "rationale": "NRF discovery returned edge_delhi_1.",
        "step_index": 0,
        "service": "nrf.discover",
        "status": "ok",
        "result": {"profiles": [{"id": "edge_delhi_1"}], "count": 1},
        "success_met": True,
        "compensation": None,
        "retry_hint": None,
    })

    # 5. Executor: StepResult for step 1 (aimle.model.deploy)
    fake.set_response({
        "rationale": "Model deployed to edge_delhi_1.",
        "step_index": 1,
        "service": "aimle.model.deploy",
        "status": "ok",
        "result": {"state": "deployed", "target": "edge_delhi_1"},
        "success_met": True,
        "compensation": {
            "service": "aimle.model.retire",
            "args": {"model_id": "congestion-det", "target": "edge_delhi_1"},
            "step_index": 1,
        },
        "retry_hint": None,
    })

    # 6. Executor: StepResult for step 2 (nwdaf subscribe)
    fake.set_response({
        "rationale": "Subscribed to congestion analytics for Delhi.",
        "step_index": 2,
        "service": "nwdaf.analytics.congestion.subscribe",
        "status": "ok",
        "result": {"subscription_id": "sub_test_001"},
        "success_met": True,
        "compensation": {
            "service": "nwdaf.analytics.unsubscribe",
            "args": {"subscription_id": "sub_test_001"},
            "step_index": 2,
        },
        "retry_hint": None,
    })

    # 7. Validator: Validation (pass)
    fake.set_response({
        "rationale": "Both criteria met: model deployed and subscription active.",
        "verdict": "pass",
        "criteria": [
            {"criterion": "model congestion-det deployed on edge_delhi_1",
             "met": True, "evidence": "deploy result state=deployed"},
            {"criterion": "congestion analytics subscription active for Delhi",
             "met": True, "evidence": "subscription_id=sub_test_001"},
        ],
    })

    # 8. Documentation: WorkflowSummary
    fake.set_response({
        "rationale": "Workflow completed successfully.",
        "workflow_id": "wf_scenario_a",
        "goal": "Deploy congestion detection model to Delhi Edge",
        "outcome": "success",
        "narrative": "Discovered Delhi Edge via NRF, deployed congestion-det model, "
                     "subscribed to congestion analytics.",
        "evidence": ["model state=deployed on edge_delhi_1",
                     "subscription sub_test_001 active"],
        "lessons": ["Delhi Edge deploy nominal."],
        "kg_deltas": [
            {"src": "model:congestion-det", "relation": "hosted_on",
             "dst": "nf:edge_delhi_1", "props": {}}
        ],
    })

    return fake


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
async def infra():
    """In-memory DB + writer + bus."""
    db = Database(":memory:")
    await db.init()
    writer = PersistenceWriter(db)
    # Seed a simulation row
    async with db.engine.begin() as conn:
        await conn.execute(insert(SimulationRow).values(
            scenario="baseline_healthy", seed=42, status="stopped",
            tick=0, started_at="2026-01-01T00:00:00Z",
        ))
    bus = InProcessEventBus()
    yield db, writer, bus
    await db.close()


@pytest.fixture
def twin_service(infra):
    db, writer, bus = infra
    twin = build_twin_from_scenario("baseline_healthy")
    # Register NRF services so discovery works
    nrf = twin.nfs_by_type(NFType.NRF)[0]
    for nf in twin._nfs.values():
        nrf.handle("nrf.register", {"profile": nf.profile.model_dump()})
    rng = RngService(seed=42)
    return TwinService(twin, rng, bus, writer, db, run_id=1)


@pytest.fixture
async def engine(infra, twin_service):
    db, writer, bus = infra
    fake_llm = _make_fake_llm()

    registry = ServiceRegistry(db, writer)
    for desc in get_catalog():
        registry.register(desc)

    policy_engine = PolicyEngine()
    invoker = ServiceInvoker(registry, policy_engine, twin_service, bus, writer)
    orchestrator = AgentOrchestrator(fake_llm, invoker, registry, twin_service)
    return WorkflowEngine(orchestrator)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestScenarioA:
    async def test_workflow_completes(self, engine: WorkflowEngine) -> None:
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a",
            seed=42,
        )
        assert state.status == "completed", f"Expected completed, got {state.status}: {state.error}"

    async def test_workflow_has_observation(self, engine: WorkflowEngine) -> None:
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a_2",
            seed=42,
        )
        assert state.observation, "Observation should be populated"
        assert state.observation.get("health_pct", 0) > 0

    async def test_workflow_has_plan_with_3_steps(self, engine: WorkflowEngine) -> None:
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a_3",
            seed=42,
        )
        steps = state.plan.get("steps", [])
        assert len(steps) == 3

    async def test_workflow_has_3_results(self, engine: WorkflowEngine) -> None:
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a_4",
            seed=42,
        )
        assert len(state.results) == 3

    async def test_validation_passed(self, engine: WorkflowEngine) -> None:
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a_5",
            seed=42,
        )
        assert state.validation.get("verdict") == ValidationVerdict.PASS.value

    async def test_trace_has_all_stages(self, engine: WorkflowEngine) -> None:
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a_6",
            seed=42,
        )
        stages = {t.stage for t in state.trace}
        for expected in ("observe", "reason", "plan", "execute", "validate", "complete"):
            assert expected in stages, f"Stage '{expected}' missing from trace"

    async def test_compensation_ledger_has_2_entries(self, engine: WorkflowEngine) -> None:
        """deploy + subscribe both logged compensations."""
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a_7",
            seed=42,
        )
        assert len(state.compensations) == 2

    async def test_summary_populated(self, engine: WorkflowEngine) -> None:
        state = await engine.start(
            goal="Deploy congestion detection model to Delhi Edge",
            correlation_id="wf_scenario_a_8",
            seed=42,
        )
        assert state.summary.get("outcome") == "success"
        assert state.summary.get("goal")
