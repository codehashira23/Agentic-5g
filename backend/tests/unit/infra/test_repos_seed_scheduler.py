"""C068-C070: Tests for repositories, seed, and sim scheduler."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.domain.agents.memory import KnowledgeEdge, KnowledgeNode, MemoryRecord
from app.domain.agents.models import MemoryScope
from app.domain.services.policy import BUILTIN_POLICIES
from app.infrastructure.db.engine import Database
from app.infrastructure.db.repos.log_repo import LogRepository
from app.infrastructure.db.repos.memory_store import SqlMemoryStore
from app.infrastructure.db.repos.policy_store import SqlPolicyStore
from app.infrastructure.db.repos.workflow_repo import WorkflowRepository
from app.infrastructure.db.seed import seed
from app.infrastructure.sim.scheduler import SimScheduler, SimTick
from app.infrastructure.writer.writer import PersistenceWriter


@pytest.fixture
async def db_writer():
    d = Database(":memory:")
    await d.init()
    w = PersistenceWriter(d)
    yield d, w
    await d.close()


# ===========================================================================
# LogRepository
# ===========================================================================
class TestLogRepository:
    async def test_append_and_read_log(self, db_writer) -> None:
        db, writer = db_writer
        repo = LogRepository(db, writer)
        await repo.append_log("info", "test message", correlation_id="wf_001")
        batch = await writer._drain(200)
        await writer._commit(batch)
        logs = await repo.get_logs(correlation_id="wf_001")
        assert len(logs) == 1
        assert logs[0]["message"] == "test message"

    async def test_append_and_read_event(self, db_writer) -> None:
        db, writer = db_writer
        repo = LogRepository(db, writer)
        await repo.append_event("NF_FAILED", {"entity": "nrf_1"},
                                correlation_id="wf_002", entity_id="nrf_1", tick=5)
        batch = await writer._drain(200)
        await writer._commit(batch)
        events = await repo.get_events(correlation_id="wf_002")
        assert len(events) == 1
        assert events[0]["type"] == "NF_FAILED"


# ===========================================================================
# WorkflowRepository
# ===========================================================================
class TestWorkflowRepository:
    async def test_save_and_get_workflow(self, db_writer) -> None:
        db, writer = db_writer
        repo = WorkflowRepository(db, writer)
        await repo.save_workflow("wf_001", {
            "goal": "Deploy model", "status": "running",
            "stage": "observe", "trigger": "user", "attempts": 0,
        })
        batch = await writer._drain(200)
        await writer._commit(batch)
        wf = await repo.get_workflow("wf_001")
        assert wf is not None
        assert wf["goal"] == "Deploy model"

    async def test_list_workflows(self, db_writer) -> None:
        db, writer = db_writer
        repo = WorkflowRepository(db, writer)
        for i in range(3):
            await repo.save_workflow(f"wf_00{i}", {
                "goal": f"Goal {i}", "status": "completed",
                "stage": "complete", "trigger": "user", "attempts": 0,
            })
        batch = await writer._drain(200)
        await writer._commit(batch)
        wfs = await repo.list_workflows(status="completed")
        assert len(wfs) == 3

    async def test_append_trace(self, db_writer) -> None:
        db, writer = db_writer
        repo = WorkflowRepository(db, writer)
        await repo.save_workflow("wf_001", {
            "goal": "test", "status": "running", "stage": "observe",
            "trigger": "user", "attempts": 0,
        })
        # Flush writer before inserting trace (FK dependency)
        batch = await writer._drain(200)
        await writer._commit(batch)
        await repo.append_trace({
            "workflow_id": "wf_001", "correlation_id": "wf_001",
            "stage": "observe",
            # agent_role intentionally omitted — avoids FK to agents table
            "rationale": "Network is healthy.",
        })
        batch = await writer._drain(200)
        await writer._commit(batch)
        trace = await repo.get_trace("wf_001")
        assert len(trace) == 1
        assert trace[0]["stage"] == "observe"


# ===========================================================================
# PolicyStore
# ===========================================================================
class TestPolicyStore:
    async def test_save_and_get_policy(self, db_writer) -> None:
        db, writer = db_writer
        store = SqlPolicyStore(db, writer)
        policy = BUILTIN_POLICIES[0]   # PLC-1
        await store.save(policy)
        batch = await writer._drain(200)
        await writer._commit(batch)
        loaded = await store.get(policy.id)
        assert loaded is not None
        assert loaded.id == "PLC-1"

    async def test_load_all(self, db_writer) -> None:
        db, writer = db_writer
        store = SqlPolicyStore(db, writer)
        for p in BUILTIN_POLICIES:
            await store.save(p)
        batch = await writer._drain(200)
        await writer._commit(batch)
        all_policies = await store.load_all()
        assert len(all_policies) == 6

    async def test_policy_round_trip_preserves_fields(self, db_writer) -> None:
        db, writer = db_writer
        store = SqlPolicyStore(db, writer)
        p = BUILTIN_POLICIES[0]
        await store.save(p)
        batch = await writer._drain(200)
        await writer._commit(batch)
        loaded = await store.get(p.id)
        assert loaded.builtin is True
        assert loaded.enabled is True
        assert "nrf.deregister" in loaded.match_services


# ===========================================================================
# MemoryStore
# ===========================================================================
class TestMemoryStore:
    async def test_save_and_get_record(self, db_writer) -> None:
        db, writer = db_writer
        store = SqlMemoryStore(db, writer)
        record = MemoryRecord(
            id="mem_001", scope=MemoryScope.EPISODIC,
            content={"goal": "deploy"}, summary="Deployed model",
            # No provenance_workflow_id — avoids FK constraint in unit test
            created_at=datetime.now(timezone.utc),
        )
        await store.save_record(record)
        batch = await writer._drain(200)
        await writer._commit(batch)
        loaded = await store.get_record("mem_001")
        assert loaded is not None
        assert loaded.summary == "Deployed model"

    async def test_get_records_by_scope(self, db_writer) -> None:
        db, writer = db_writer
        store = SqlMemoryStore(db, writer)
        for i in range(3):
            await store.save_record(MemoryRecord(
                id=f"mem_{i:03d}", scope=MemoryScope.EPISODIC,
                content={}, summary=f"Memory {i}",
                created_at=datetime.now(timezone.utc),
                # No provenance_workflow_id — avoids FK constraint
            ))
        batch = await writer._drain(200)
        await writer._commit(batch)
        records = await store.get_records(MemoryScope.EPISODIC)
        assert len(records) == 3

    async def test_upsert_knowledge_node(self, db_writer) -> None:
        db, writer = db_writer
        store = SqlMemoryStore(db, writer)
        node = KnowledgeNode(id="nf:upf_1", entity_type="nf", label="UPF Delhi 1")
        await store.upsert_node(node)
        batch = await writer._drain(200)
        await writer._commit(batch)
        nbr = await store.get_neighbourhood("nf:upf_1")
        assert nbr["node_id"] == "nf:upf_1"

    async def test_upsert_knowledge_edge(self, db_writer) -> None:
        db, writer = db_writer
        store = SqlMemoryStore(db, writer)
        node_a = KnowledgeNode(id="model:m1", entity_type="model", label="M1")
        node_b = KnowledgeNode(id="nf:edge_1", entity_type="nf", label="Edge 1")
        await store.upsert_node(node_a)
        await store.upsert_node(node_b)
        edge = KnowledgeEdge(src_id="model:m1", relation="hosted_on", dst_id="nf:edge_1")
        await store.upsert_edge(edge)
        batch = await writer._drain(200)
        await writer._commit(batch)
        nbr = await store.get_neighbourhood("model:m1")
        assert len(nbr["edges_out"]) == 1
        assert nbr["edges_out"][0]["relation"] == "hosted_on"


# ===========================================================================
# Seed
# ===========================================================================
class TestSeed:
    async def test_seed_creates_policies(self, db_writer) -> None:
        db, writer = db_writer
        await seed(db, writer)
        store = SqlPolicyStore(db, writer)
        policies = await store.load_all()
        assert len(policies) == 6

    async def test_seed_idempotent(self, db_writer) -> None:
        db, writer = db_writer
        await seed(db, writer)
        await seed(db, writer)   # run twice
        store = SqlPolicyStore(db, writer)
        policies = await store.load_all()
        assert len(policies) == 6   # still 6, not 12

    async def test_seed_creates_agents(self, db_writer) -> None:
        from sqlalchemy import text
        db, writer = db_writer
        await seed(db, writer)
        async with db.session() as s:
            result = await s.execute(text("SELECT COUNT(*) FROM agents"))
            count = result.scalar()
        assert count == 7

    async def test_seed_creates_simulation_row(self, db_writer) -> None:
        from sqlalchemy import text
        db, writer = db_writer
        await seed(db, writer)
        async with db.session() as s:
            result = await s.execute(text("SELECT seed FROM simulation"))
            s_val = result.scalar()
        assert s_val == 42


# ===========================================================================
# SimScheduler (C070)
# ===========================================================================
class TestSimScheduler:
    async def test_step_increments_tick(self) -> None:
        sched = SimScheduler(tick_ms=100)
        await sched.step(3)
        assert sched.tick == 3

    async def test_step_calls_on_tick(self) -> None:
        ticks_received: list[int] = []

        async def handler(evt: SimTick) -> None:
            ticks_received.append(evt.tick)

        sched = SimScheduler(tick_ms=100, on_tick=handler)
        await sched.step(5)
        assert ticks_received == [1, 2, 3, 4, 5]

    async def test_pause_stops_running(self) -> None:
        sched = SimScheduler()
        sched.start()
        assert sched.running is True
        sched.pause()
        assert sched.running is False

    async def test_reset_zeroes_tick(self) -> None:
        sched = SimScheduler()
        await sched.step(10)
        sched.reset()
        assert sched.tick == 0

    async def test_sim_tick_event_has_correct_type(self) -> None:
        sched = SimScheduler()
        events: list[SimTick] = []

        async def h(e: SimTick) -> None:
            events.append(e)

        sched._on_tick = h
        await sched.step(1)
        assert events[0].type == "SIM_TICK"
        assert events[0].tick == 1
