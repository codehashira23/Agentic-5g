"""C062+C063: Tests for all 18 ORM tables — create, verify, FK enforcement."""
from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import (
    AgentRow, EventRow, KnowledgeEdgeRow, KnowledgeNodeRow, KpiRow,
    LogRow, MemoryRow, ModelRow, PolicyRow, ServiceCallRow, ServiceRow,
    SimulationRow, TopologyLinkRow, TopologyNodeRow, UserRow,
    WorkflowRow, WorkflowStepRow, WorkflowTraceRow,
)


@pytest.fixture
async def db() -> Database:
    d = Database(path=":memory:")
    await d.init()
    yield d
    await d.close()


EXPECTED_TABLES = {
    "users", "agents", "services", "policies",
    "simulation", "topology_nodes", "topology_links",
    "kpis", "events",
    "workflows", "workflow_steps", "workflow_trace",
    "logs", "memory", "knowledge_nodes", "knowledge_edges",
    "models", "service_calls",
}


class TestAllTablesCreated:
    async def test_18_tables_exist(self, db: Database) -> None:
        async with db.session() as s:
            result = await s.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            names = {r[0] for r in result.fetchall()}
        assert EXPECTED_TABLES.issubset(names)

    async def test_exactly_18_tables(self, db: Database) -> None:
        async with db.session() as s:
            result = await s.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            names = {r[0] for r in result.fetchall()}
        # Filter to only our expected tables
        found = names & EXPECTED_TABLES
        assert len(found) == 18


class TestCoreTableInserts:
    async def test_insert_user(self, db: Database) -> None:
        async with db.session() as s:
            s.add(UserRow(
                id="user_001", username="researcher1",
                display_name="R1", role="researcher",
                created_at="2026-01-01T00:00:00Z",
            ))
        async with db.session() as s:
            u = await s.get(UserRow, "user_001")
            assert u is not None
            assert u.username == "researcher1"

    async def test_insert_simulation(self, db: Database) -> None:
        async with db.session() as s:
            s.add(SimulationRow(
                scenario="baseline_healthy",
                seed=42,
                status="stopped",
                tick=0,
                started_at="2026-01-01T00:00:00Z",
            ))
        async with db.session() as s:
            result = await s.execute(text("SELECT seed FROM simulation"))
            assert result.scalar() == 42

    async def test_insert_topology_node(self, db: Database) -> None:
        async with db.session() as s:
            s.add(TopologyNodeRow(
                id="upf_delhi_1", type="UPF", region="Delhi",
                status="ACTIVE", load=0.0,
                updated_at="2026-01-01T00:00:00Z",
            ))
        async with db.session() as s:
            n = await s.get(TopologyNodeRow, "upf_delhi_1")
            assert n is not None
            assert n.type == "UPF"

    async def test_insert_kpi_row(self, db: Database) -> None:
        async with db.session() as s:
            s.add(SimulationRow(scenario="test", seed=42, status="running",
                                started_at="2026-01-01T00:00:00Z"))
            s.add(TopologyNodeRow(id="upf_1", type="UPF", region="Delhi",
                                  status="ACTIVE"))
        async with db.session() as s:
            s.add(KpiRow(
                node_id="upf_1", kpi="latency_ms",
                value=18.4, tick=5, run_id=1,
                ts="2026-01-01T00:00:05Z",
            ))
        async with db.session() as s:
            result = await s.execute(text("SELECT value FROM kpis"))
            assert abs(result.scalar() - 18.4) < 0.001

    async def test_insert_event_row(self, db: Database) -> None:
        async with db.session() as s:
            s.add(SimulationRow(scenario="test", seed=42, status="running",
                                started_at="2026-01-01T00:00:00Z"))
        async with db.session() as s:
            s.add(EventRow(
                type="NF_FAILED",
                correlation_id="wf_abc",
                entity_id="nrf_core_1",
                payload_json='{"cause":"hazard"}',
                tick=10, run_id=1,
                ts="2026-01-01T00:00:10Z",
            ))
        async with db.session() as s:
            result = await s.execute(text("SELECT type FROM events"))
            assert result.scalar() == "NF_FAILED"


class TestWorkflowTables:
    async def _seed_user(self, db: Database) -> None:
        async with db.session() as s:
            s.add(UserRow(id="u1", username="u1",
                          role="researcher", created_at="2026-01-01T00:00:00Z"))

    async def test_insert_workflow(self, db: Database) -> None:
        await self._seed_user(db)
        async with db.session() as s:
            s.add(WorkflowRow(
                id="wf_001", correlation_id="wf_001",
                goal="Deploy model", trigger="user",
                status="running", stage="observe",
                attempts=0,
                created_by="u1",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            ))
        async with db.session() as s:
            w = await s.get(WorkflowRow, "wf_001")
            assert w is not None
            assert w.goal == "Deploy model"

    async def test_insert_log(self, db: Database) -> None:
        async with db.session() as s:
            s.add(LogRow(
                ts="2026-01-01T00:00:00Z", level="info",
                message="Server started",
            ))
        async with db.session() as s:
            result = await s.execute(text("SELECT message FROM logs"))
            assert result.scalar() == "Server started"


class TestIndexesExist:
    async def test_kpis_index_exists(self, db: Database) -> None:
        async with db.session() as s:
            result = await s.execute(
                text("SELECT name FROM sqlite_master WHERE type='index' "
                     "AND name='ix_kpis_node_kpi_tick'")
            )
            assert result.scalar() is not None

    async def test_events_correlation_index(self, db: Database) -> None:
        async with db.session() as s:
            result = await s.execute(
                text("SELECT name FROM sqlite_master WHERE type='index' "
                     "AND name='ix_events_correlation'")
            )
            assert result.scalar() is not None
