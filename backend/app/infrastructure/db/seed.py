"""
Idempotent database seeder.
Inserts built-in policies, agent specs, a default user, and a default
simulation run row. Safe to run multiple times (upsert by PK).

Run automatically in the lifespan (C101) and via scripts/seed.ps1.
Owning docs: 12-database.md §10
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.domain.services.policy import BUILTIN_POLICIES
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import (
    AgentRow,
    SimulationRow,
    UserRow,
)
from app.infrastructure.db.repos.policy_store import SqlPolicyStore
from app.infrastructure.writer.writer import PersistenceWriter


async def seed(
    db: Database,
    writer: PersistenceWriter,
    scenario: str = "baseline_healthy",
    seed_value: int = 42,
) -> None:
    """Idempotent seed — upsert all built-in rows."""
    policy_store = SqlPolicyStore(db, writer)
    now = datetime.now(UTC).isoformat()

    # 1. Built-in policies (PLC-1..6)
    for policy in BUILTIN_POLICIES:
        existing = await policy_store.get(policy.id)
        if existing is None:
            await policy_store.save(policy)

    # 2. Agent spec rows
    agent_specs = [
        ("planner", '["nrf.discover","twin.snapshot","memory.read"]', '["episodic","semantic"]'),
        ("executor", '["aimle.model.deploy","upf.loadbalance.apply"]', "[]"),
        ("observer", '["twin.snapshot","nwdaf.analytics.congestion.query"]', "[]"),
        ("optimizer", '["dcf.data.history","nwdaf.analytics.load.query"]', '["semantic"]'),
        ("recovery", '["aimle.model.retire","nwdaf.analytics.unsubscribe"]', "[]"),
        ("documentation", '["twin.snapshot"]', "[]"),
        ("memory", '["memory.write","knowledge.upsert"]', '["episodic","semantic"]'),
    ]
    async with db.session() as s:
        for role, tools, scopes in agent_specs:
            existing_agent = await s.get(AgentRow, role)
            if existing_agent is None:
                s.add(AgentRow(
                    role=role,
                    description=f"{role.capitalize()} agent",
                    tools_json=tools,
                    memory_scopes_json=scopes,
                    enabled=1,
                    created_at=now,
                ))

    # 3. Default user
    async with db.session() as s:
        existing_user = await s.get(UserRow, "user_default")
        if existing_user is None:
            s.add(UserRow(
                id="user_default",
                username="researcher",
                display_name="Default Researcher",
                role="researcher",
                created_at=now,
            ))

    # 4. Default simulation run row (run_id=1)
    async with db.session() as s:
        existing_sim = await s.get(SimulationRow, 1)
        if existing_sim is None:
            s.add(SimulationRow(
                scenario=scenario,
                seed=seed_value,
                status="stopped",
                tick=0,
                tick_ms=1000,
                started_at=now,
            ))

    # Flush writer so everything is committed
    batch = await writer._drain(500)
    if batch:
        await writer._commit(batch)
