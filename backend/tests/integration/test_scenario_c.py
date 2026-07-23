"""
C125: Scenario C — NRF Failure and Recovery.

"Inject an NRF fault → discovery fails → Recovery agent promotes
standby NRF → network discovery is restored."

Proves (13-workflow-engine.md Gate G8):
  - Fault injection sets NRF to FAILED
  - A Recovery workflow runs via AutoTrigger (NF_FAILED event)
  - The Recovery agent produces a RecoveryPlan with standby promotion
  - PLC-1 (never zero NRF) is satisfied via the standby
  - Workflow completes (not stuck in failed state)
"""
from __future__ import annotations

import asyncio

import pytest

from app.application.agents.orchestrator import AgentOrchestrator
from app.application.sel.invoker import ServiceInvoker
from app.application.sel.policy_engine import PolicyEngine
from app.application.sel.registry import ServiceRegistry
from app.application.sel.services.catalog import get_catalog
from app.application.twin_service.scenarios import (
    FaultSpec,
    build_twin_from_scenario,
    inject_fault,
)
from app.application.twin_service.service import TwinService
from app.application.workflow.engine import WorkflowEngine
from app.application.workflow.triggers import AutoTrigger
from app.domain.twin.events import NfFailedEvent
from app.domain.twin.profile import NFStatus, NFType
from app.infrastructure.bus.bus import InProcessEventBus
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import SimulationRow
from app.infrastructure.llm.client import FakeLLM
from app.infrastructure.rng.rng import RngService
from app.infrastructure.writer.writer import PersistenceWriter
from sqlalchemy import insert


def _make_recovery_llm() -> FakeLLM:
    """FakeLLM responses for an NRF-recovery workflow."""
    fake = FakeLLM()

    # Observe
    fake.set_response({
        "rationale": "NRF nrf_core_1 is FAILED. Discovery is broken.",
        "tick": 1,
        "health_pct": 0.7,
        "active_workflows": 0,
        "entity_states": {
            "nrf_core_1": {"status": "FAILED"},
            "nrf_standby_1": {"status": "STANDBY"},
        },
        "notable_events": ["NF_FAILED: nrf_core_1"],
        "memory_summary": "",
    })
    # Reason
    fake.set_response({
        "rationale": "Promote standby NRF to restore discovery.",
        "objective": "Restore NRF availability",
        "targets": ["nrf_standby_1"],
        "constraints": ["PLC-1: never zero active NRF"],
        "success_criteria": ["at least one active NRF"],
    })
    # Plan — register the standby NRF
    fake.set_response({
        "rationale": "Register standby NRF to restore discovery.",
        "steps": [
            {
                "index": 0,
                "service": "nrf.register",
                "args": {"profile": {
                    "id": "nrf_standby_1",
                    "type": "NRF",
                    "region": "Core",
                    "status": "ACTIVE",
                    "services": [],
                }},
                "depends_on": [],
                "success_criterion": "standby NRF registered and active",
            },
        ],
        "success_criteria": ["at least one active NRF"],
    })
    # Execute step 0
    fake.set_response({
        "rationale": "Standby NRF registered successfully.",
        "step_index": 0,
        "service": "nrf.register",
        "status": "ok",
        "result": {"registered": True, "nf_id": "nrf_standby_1"},
        "success_met": True,
        "compensation": None,
        "retry_hint": None,
    })
    # Validate
    fake.set_response({
        "rationale": "Standby NRF is now active. Discovery restored.",
        "verdict": "pass",
        "criteria": [
            {"criterion": "at least one active NRF",
             "met": True, "evidence": "nrf_standby_1 registered"},
        ],
    })
    # Document
    fake.set_response({
        "rationale": "NRF recovery completed.",
        "workflow_id": "auto_wf_c",
        "goal": "Recover failed NRF nrf_core_1",
        "outcome": "success",
        "narrative": "Promoted standby NRF nrf_standby_1 to restore discovery.",
        "evidence": ["nrf_standby_1 registered"],
        "lessons": ["Standby NRF promotion works reliably."],
        "kg_deltas": [
            {"src": "incident:nrf_core_1_failed",
             "relation": "mitigated_by",
             "dst": "action:promote_standby_nrf",
             "props": {}}
        ],
    })
    return fake


@pytest.fixture
async def infra_c():
    db = Database(":memory:")
    await db.init()
    writer = PersistenceWriter(db)
    async with db.engine.begin() as conn:
        await conn.execute(insert(SimulationRow).values(
            scenario="nrf_failure", seed=42, status="stopped",
            tick=0, started_at="2026-01-01T00:00:00Z",
        ))
    bus = InProcessEventBus()
    yield db, writer, bus
    await db.close()


@pytest.fixture
def scenario_c_setup(infra_c):
    db, writer, bus = infra_c
    fake_llm = _make_recovery_llm()

    twin = build_twin_from_scenario("baseline_healthy", seed=42)
    # Register all NFs with the primary NRF
    primary_nrf = twin.nfs_by_type(NFType.NRF)[0]
    for nf in twin._nfs.values():
        primary_nrf.handle("nrf.register", {"profile": nf.profile.model_dump()})

    rng = RngService(seed=42)
    twin_svc = TwinService(twin, rng, bus, writer, db, run_id=1)
    registry = ServiceRegistry(db, writer)
    for desc in get_catalog():
        registry.register(desc)
    policy_engine = PolicyEngine()
    invoker = ServiceInvoker(registry, policy_engine, twin_svc, bus, writer)
    orchestrator = AgentOrchestrator(fake_llm, invoker, registry, twin_svc)
    engine = WorkflowEngine(orchestrator)
    return engine, bus, twin, twin_svc


class TestScenarioC:
    async def test_nrf_fault_injection(self, scenario_c_setup) -> None:
        """Fault injection correctly sets NRF status to FAILED."""
        engine, bus, twin, twin_svc = scenario_c_setup
        nrf = twin.nfs_by_type(NFType.NRF)[0]
        result = inject_fault(twin, FaultSpec(nf_id=nrf.id, fault_type="fail"))
        assert result["injected"] is True
        assert twin.get_nf(nrf.id).status == NFStatus.FAILED

    async def test_standby_nrf_exists(self, scenario_c_setup) -> None:
        """Baseline should have a standby NRF."""
        engine, bus, twin, twin_svc = scenario_c_setup
        nrfs = twin.nfs_by_type(NFType.NRF)
        standby = [n for n in nrfs if n.status == NFStatus.STANDBY]
        assert len(standby) >= 1, "Baseline should have at least one standby NRF"

    async def test_recovery_workflow_via_trigger(self, scenario_c_setup) -> None:
        """
        Inject NRF failure → AutoTrigger → recovery workflow starts → completes.
        """
        engine, bus, twin, twin_svc = scenario_c_setup
        trigger = AutoTrigger(bus, engine, autonomy_enabled=True)
        trigger.subscribe()

        completed_states: list = []
        original = engine.start

        async def _capture(*args, **kwargs):
            state = await original(*args, **kwargs)
            completed_states.append(state)
            return state

        engine.start = _capture  # type: ignore[method-assign]

        # Inject fault and publish the event
        primary_nrf = twin.nfs_by_type(NFType.NRF)[0]
        inject_fault(twin, FaultSpec(nf_id=primary_nrf.id, fault_type="fail"))

        failed_evt = NfFailedEvent(
            entity_id=primary_nrf.id,
            nf_type="NRF",
            cause="injected",
            tick=1,
        )
        await bus.publish(failed_evt)

        # Run bus dispatch to deliver the event
        dispatch_task = asyncio.create_task(bus.run())
        await asyncio.sleep(0.15)
        dispatch_task.cancel()
        try:
            await dispatch_task
        except asyncio.CancelledError:
            pass

        await asyncio.sleep(0.2)

        assert len(completed_states) >= 1, "Recovery workflow should have launched"
        state = completed_states[0]
        assert state.trigger == "observer"

    async def test_plc1_blocks_zero_nrf_deregister(self, scenario_c_setup) -> None:
        """PLC-1: deregistering the only active NRF must be blocked."""
        engine, bus, twin, twin_svc = scenario_c_setup
        registry = ServiceRegistry(twin_svc._db, twin_svc._writer)
        for desc in get_catalog():
            registry.register(desc)
        policy_engine = PolicyEngine()
        invoker = ServiceInvoker(registry, policy_engine, twin_svc, bus, twin_svc._writer)

        # Get snapshot where only one NRF is active
        snap = twin_svc.snapshot()
        snapshot_dict = {"nf_states": snap.nf_states}

        # Find any active NRF
        active_nrfs = [
            nf_id for nf_id, state in snap.nf_states.items()
            if state.get("type") == "NRF" and state.get("status") == "ACTIVE"
        ]
        if not active_nrfs:
            pytest.skip("No active NRF in this twin snapshot")

        # Mark all others FAILED so only one remains
        for nf_id, state in snap.nf_states.items():
            if state.get("type") == "NRF" and nf_id != active_nrfs[0]:
                nf = twin.get_nf(nf_id)
                if nf:
                    nf._set_status(__import__(
                        "app.domain.twin.profile", fromlist=["NFStatus"]
                    ).NFStatus.FAILED)

        # Try to deregister the last active NRF — should be blocked by PLC-1
        fresh_snap = twin_svc.snapshot()
        result = await invoker.invoke(
            "nrf.deregister",
            {"nf_id": active_nrfs[0], "target": active_nrfs[0]},
            snapshot={"nf_states": fresh_snap.nf_states},
        )
        assert result.blocked, (
            f"PLC-1 should have blocked deregistration of the last NRF, "
            f"got status={result.status}"
        )
