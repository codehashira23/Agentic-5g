"""
C123: Scenario B — Autonomous Mitigation (no human prompt).

"A KPI_THRESHOLD_BREACH fires on Mumbai UPF and the Observer
triggers a mitigation workflow autonomously."

Proves (13-workflow-engine.md Gate G8):
  - AutoTrigger subscribes to breach events
  - A breach event causes a new workflow with trigger='observer'
  - The FakeLLM-driven workflow completes with status='completed'
  - De-duplication prevents duplicate workflows for the same key
"""
from __future__ import annotations

import asyncio

import pytest

from app.application.agents.orchestrator import AgentOrchestrator
from app.application.sel.invoker import ServiceInvoker
from app.application.sel.policy_engine import PolicyEngine
from app.application.sel.registry import ServiceRegistry
from app.application.sel.services.catalog import get_catalog
from app.application.twin_service.scenarios import build_twin_from_scenario
from app.application.twin_service.service import TwinService
from app.application.workflow.engine import WorkflowEngine
from app.application.workflow.triggers import AutoTrigger
from app.domain.twin.events import KpiThresholdBreachEvent
from app.domain.twin.profile import NFType
from app.infrastructure.bus.bus import InProcessEventBus
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import SimulationRow
from app.infrastructure.llm.client import FakeLLM
from app.infrastructure.rng.rng import RngService
from app.infrastructure.writer.writer import PersistenceWriter
from sqlalchemy import insert


def _make_mitigation_llm() -> FakeLLM:
    """FakeLLM with responses for a mitigation workflow."""
    fake = FakeLLM()
    # Observe
    fake.set_response({
        "rationale": "Mumbai UPF latency is breaching 20ms threshold.",
        "tick": 5,
        "health_pct": 0.85,
        "active_workflows": 0,
        "entity_states": {"upf_mumbai_1": {"status": "ACTIVE", "load": 0.92}},
        "notable_events": ["KPI_THRESHOLD_BREACH on upf_mumbai_1"],
        "memory_summary": "",
    })
    # Reason (Interpretation)
    fake.set_response({
        "rationale": "Need to reduce load on Mumbai UPF.",
        "objective": "Reduce latency on Mumbai UPF below 20ms",
        "targets": ["upf_mumbai_1"],
        "constraints": ["PLC-4: Mumbai only"],
        "success_criteria": ["upf_mumbai_1 latency < 20ms"],
    })
    # Plan
    fake.set_response({
        "rationale": "Apply load-balance to shift sessions off upf_mumbai_1.",
        "steps": [
            {
                "index": 0,
                "service": "upf.loadbalance.apply",
                "args": {"fraction": 0.3, "target": "upf_mumbai_1"},
                "depends_on": [],
                "success_criterion": "load reduced",
            },
        ],
        "success_criteria": ["upf_mumbai_1 latency < 20ms"],
    })
    # Execute step 0
    fake.set_response({
        "rationale": "Load-balance applied, 30% sessions moved.",
        "step_index": 0,
        "service": "upf.loadbalance.apply",
        "status": "ok",
        "result": {"moved_count": 5, "remaining": 12},
        "success_met": True,
        "compensation": {
            "service": "upf.loadbalance.restore",
            "args": {"target": "upf_mumbai_1"},
            "step_index": 0,
        },
        "retry_hint": None,
    })
    # Validate
    fake.set_response({
        "rationale": "Load reduced; latency expected to recover.",
        "verdict": "pass",
        "criteria": [
            {"criterion": "upf_mumbai_1 latency < 20ms",
             "met": True, "evidence": "load reduced to 0.65"}
        ],
    })
    # Document
    fake.set_response({
        "rationale": "Autonomous mitigation completed successfully.",
        "workflow_id": "auto_wf_b",
        "goal": "Mitigate latency breach in Mumbai",
        "outcome": "success",
        "narrative": "Applied load-balance to upf_mumbai_1, reducing load.",
        "evidence": ["moved_count=5"],
        "lessons": ["Mumbai UPF load-balance is effective."],
        "kg_deltas": [],
    })
    return fake


@pytest.fixture
async def infra_b():
    db = Database(":memory:")
    await db.init()
    writer = PersistenceWriter(db)
    async with db.engine.begin() as conn:
        await conn.execute(insert(SimulationRow).values(
            scenario="mumbai_congestion", seed=7, status="stopped",
            tick=0, started_at="2026-01-01T00:00:00Z",
        ))
    bus = InProcessEventBus()
    yield db, writer, bus
    await db.close()


@pytest.fixture
def scenario_b_engine(infra_b):
    db, writer, bus = infra_b
    fake_llm = _make_mitigation_llm()
    twin = build_twin_from_scenario("mumbai_congestion", seed=7)
    # Register NRFs
    nrf = twin.nfs_by_type(NFType.NRF)[0]
    for nf in twin._nfs.values():
        nrf.handle("nrf.register", {"profile": nf.profile.model_dump()})
    rng = RngService(seed=7)
    twin_svc = TwinService(twin, rng, bus, writer, db, run_id=1)
    registry = ServiceRegistry(db, writer)
    for desc in get_catalog():
        registry.register(desc)
    policy_engine = PolicyEngine()
    invoker = ServiceInvoker(registry, policy_engine, twin_svc, bus, writer)
    orchestrator = AgentOrchestrator(fake_llm, invoker, registry, twin_svc)
    engine = WorkflowEngine(orchestrator)
    return engine, bus


class TestScenarioB:
    async def test_auto_trigger_launches_workflow(self, scenario_b_engine) -> None:
        """
        Publish a KPI_THRESHOLD_BREACH → AutoTrigger must launch a workflow.
        """
        engine, bus = scenario_b_engine

        trigger = AutoTrigger(bus, engine, autonomy_enabled=True)
        trigger.subscribe()

        # Drain the bus dispatch loop briefly
        completed_states: list = []

        original_start = engine.start

        async def _capturing_start(*args, **kwargs):
            state = await original_start(*args, **kwargs)
            completed_states.append(state)
            return state

        engine.start = _capturing_start  # type: ignore[method-assign]

        # Publish a breach event
        breach = KpiThresholdBreachEvent(
            entity_id="upf_mumbai_1",
            kpi="latency_ms",
            value=25.0,
            threshold=20.0,
            region="Mumbai",
            tick=5,
        )
        await bus.publish(breach)

        # Run the bus dispatch loop to deliver the event to the trigger handler
        dispatch_task = asyncio.create_task(bus.run())
        await asyncio.sleep(0.1)   # allow trigger handler + workflow to run
        dispatch_task.cancel()
        try:
            await dispatch_task
        except asyncio.CancelledError:
            pass

        # Give workflow tasks time to complete
        await asyncio.sleep(0.2)

        assert len(completed_states) >= 1, (
            "AutoTrigger should have started at least one workflow"
        )
        state = completed_states[0]
        assert state.trigger == "observer"
        assert state.status == "completed"

    async def test_auto_trigger_dedup(self, scenario_b_engine) -> None:
        """Same breach key should not launch duplicate workflows."""
        engine, bus = scenario_b_engine
        trigger = AutoTrigger(bus, engine, autonomy_enabled=True)
        trigger.subscribe()

        breach = KpiThresholdBreachEvent(
            entity_id="upf_mumbai_1",
            kpi="latency_ms",
            value=25.0,
            threshold=20.0,
            region="Mumbai",
            tick=5,
        )
        await bus.publish(breach)
        await bus.publish(breach)   # duplicate

        dispatch_task = asyncio.create_task(bus.run())
        await asyncio.sleep(0.05)
        dispatch_task.cancel()
        try:
            await dispatch_task
        except asyncio.CancelledError:
            pass

        # Only one in-flight entry should exist for this key
        assert trigger.in_flight_count <= 1

    async def test_auto_trigger_disabled(self, scenario_b_engine) -> None:
        """With autonomy disabled, no workflow should be launched."""
        engine, bus = scenario_b_engine
        trigger = AutoTrigger(bus, engine, autonomy_enabled=False)
        trigger.subscribe()

        started: list = []
        original = engine.start

        async def _track(*a, **kw):
            r = await original(*a, **kw)
            started.append(r)
            return r

        engine.start = _track  # type: ignore[method-assign]

        breach = KpiThresholdBreachEvent(
            entity_id="upf_mumbai_1", kpi="latency_ms",
            value=25.0, threshold=20.0, region="Mumbai", tick=5,
        )
        await bus.publish(breach)

        dispatch_task = asyncio.create_task(bus.run())
        await asyncio.sleep(0.05)
        dispatch_task.cancel()
        try:
            await dispatch_task
        except asyncio.CancelledError:
            pass

        assert len(started) == 0, "No workflow should start when autonomy is disabled"
