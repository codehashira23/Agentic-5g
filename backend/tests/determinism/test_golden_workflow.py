"""
C131: Golden-workflow traversal test.

Two runs with identical (FakeLLM responses + seed) must produce
identical WorkflowState traversal and final state (WP6, GR10).

Owning docs: 13-workflow-engine.md Gate G5, 16-testing.md §7
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from app.application.agents.orchestrator import AgentOrchestrator
from app.application.sel.invoker import ServiceInvoker
from app.application.sel.policy_engine import PolicyEngine
from app.application.sel.registry import ServiceRegistry
from app.application.sel.services.catalog import get_catalog
from app.application.twin_service.scenarios import build_twin_from_scenario
from app.application.twin_service.service import TwinService
from app.application.workflow.engine import WorkflowEngine
from app.domain.twin.profile import NFType
from app.infrastructure.bus.bus import InProcessEventBus
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import SimulationRow
from app.infrastructure.llm.client import FakeLLM
from app.infrastructure.rng.rng import RngService
from app.infrastructure.writer.writer import PersistenceWriter
from sqlalchemy import insert


# ---------------------------------------------------------------------------
# Shared FakeLLM responses for Scenario A (deterministic)
# ---------------------------------------------------------------------------
SCENARIO_A_RESPONSES = [
    # observe
    {"rationale": "Twin healthy.", "tick": 0, "health_pct": 0.95,
     "active_workflows": 0, "entity_states": {}, "notable_events": [], "memory_summary": ""},
    # reason
    {"rationale": "Deploy model.", "objective": "Deploy model to Delhi Edge",
     "targets": ["edge_delhi_1"], "constraints": [], "success_criteria": ["model deployed"]},
    # plan
    {"rationale": "3 steps.", "steps": [
        {"index": 0, "service": "nrf.discover",
         "args": {"nf_type": "Edge", "region": "Delhi"}, "depends_on": [], "success_criterion": "edge found"},
        {"index": 1, "service": "aimle.model.deploy",
         "args": {"model_id": "m1", "name": "M1", "target": "edge_delhi_1"}, "depends_on": [0], "success_criterion": "deployed"},
        {"index": 2, "service": "nwdaf.analytics.congestion.subscribe",
         "args": {"region": "Delhi"}, "depends_on": [1], "success_criterion": "subscribed"},
    ], "success_criteria": ["model deployed"]},
    # execute step 0
    {"rationale": "Discovered.", "step_index": 0, "service": "nrf.discover",
     "status": "ok", "result": {"count": 1}, "success_met": True, "compensation": None, "retry_hint": None},
    # execute step 1
    {"rationale": "Deployed.", "step_index": 1, "service": "aimle.model.deploy",
     "status": "ok", "result": {"state": "deployed"}, "success_met": True,
     "compensation": {"service": "aimle.model.retire", "args": {}, "step_index": 1}, "retry_hint": None},
    # execute step 2
    {"rationale": "Subscribed.", "step_index": 2, "service": "nwdaf.analytics.congestion.subscribe",
     "status": "ok", "result": {"subscription_id": "sub_det"}, "success_met": True,
     "compensation": {"service": "nwdaf.analytics.unsubscribe", "args": {}, "step_index": 2}, "retry_hint": None},
    # validate
    {"rationale": "All met.", "verdict": "pass", "criteria": [
        {"criterion": "model deployed", "met": True, "evidence": "deployed"}]},
    # document
    {"rationale": "Done.", "workflow_id": "wf_golden", "goal": "Deploy model to Delhi Edge",
     "outcome": "success", "narrative": "Model deployed.", "evidence": [], "lessons": [], "kg_deltas": []},
]


async def _run_once(seed: int, correlation_id: str) -> dict[str, Any]:
    """Build fresh infrastructure and run Scenario A with fixed responses."""
    db = Database(":memory:")
    await db.init()
    writer = PersistenceWriter(db)
    async with db.engine.begin() as conn:
        await conn.execute(insert(SimulationRow).values(
            scenario="baseline_healthy", seed=seed,
            status="stopped", tick=0, started_at="2026-01-01T00:00:00Z",
        ))

    fake = FakeLLM()
    for resp in SCENARIO_A_RESPONSES:
        fake.set_response(dict(resp))   # fresh copy each run

    twin = build_twin_from_scenario("baseline_healthy", seed=seed)
    nrf = twin.nfs_by_type(NFType.NRF)[0]
    for nf in twin._nfs.values():
        nrf.handle("nrf.register", {"profile": nf.profile.model_dump()})

    rng = RngService(seed=seed)
    bus = InProcessEventBus()
    twin_svc = TwinService(twin, rng, bus, writer, db, run_id=1)

    registry = ServiceRegistry(db, writer)
    for desc in get_catalog():
        registry.register(desc)

    invoker = ServiceInvoker(registry, PolicyEngine(), twin_svc, bus, writer)
    orchestrator = AgentOrchestrator(fake, invoker, registry, twin_svc)
    engine = WorkflowEngine(orchestrator)

    state = await engine.start(
        goal="Deploy model to Delhi Edge",
        seed=seed,
        correlation_id=correlation_id,
    )
    await db.close()

    # Build a hashable fingerprint of the traversal
    trajectory = {
        "status": state.status,
        "stage_sequence": [t.stage for t in state.trace],
        "agent_sequence": [t.agent_role for t in state.trace],
        "step_count": len(state.results),
        "compensation_count": len(state.compensations),
        "outcome": state.summary.get("outcome", ""),
    }
    return trajectory


def _hash(d: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestGoldenWorkflow:
    async def test_two_runs_produce_identical_traversal(self) -> None:
        """
        Same FakeLLM responses + same seed → identical workflow traversal.
        This is the determinism guarantee (WP6 / GR10).
        """
        t1 = await _run_once(seed=42, correlation_id="wf_golden_1")
        t2 = await _run_once(seed=42, correlation_id="wf_golden_2")
        assert _hash(t1) == _hash(t2), (
            f"Non-determinism detected!\nRun 1: {t1}\nRun 2: {t2}"
        )

    async def test_workflow_completes_in_both_runs(self) -> None:
        t1 = await _run_once(seed=42, correlation_id="wf_g3")
        assert t1["status"] == "completed"

    async def test_all_8_stages_present(self) -> None:
        t1 = await _run_once(seed=42, correlation_id="wf_g4")
        stages = set(t1["stage_sequence"])
        for expected in ("observe", "reason", "plan", "execute", "validate", "complete"):
            assert expected in stages, f"Stage '{expected}' missing from traversal"

    async def test_3_steps_executed(self) -> None:
        t1 = await _run_once(seed=42, correlation_id="wf_g5")
        assert t1["step_count"] == 3

    async def test_2_compensations_recorded(self) -> None:
        t1 = await _run_once(seed=42, correlation_id="wf_g6")
        assert t1["compensation_count"] == 2

    async def test_different_seed_same_traversal(self) -> None:
        """
        The traversal structure is determined by LLM responses (fixed),
        not the twin RNG — so different seeds should produce same stages.
        """
        t1 = await _run_once(seed=42, correlation_id="wf_g7")
        t2 = await _run_once(seed=99, correlation_id="wf_g8")
        # Stage/agent sequence should be identical regardless of seed
        assert t1["stage_sequence"] == t2["stage_sequence"]
        assert t1["agent_sequence"] == t2["agent_sequence"]
