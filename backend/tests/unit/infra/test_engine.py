"""C061: Tests for the async SQLite engine and Database wrapper."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.infrastructure.db.engine import Database


@pytest.fixture
async def db() -> Database:
    d = Database(path=":memory:")
    await d.init()
    yield d
    await d.close()


class TestDatabase:
    async def test_init_creates_engine(self, db: Database) -> None:
        assert db.engine is not None

    async def test_session_scope_commits(self, db: Database) -> None:
        async with db.session() as s:
            result = await s.execute(text("SELECT 1"))
            assert result.scalar() == 1

    async def test_session_rollback_on_error(self, db: Database) -> None:
        with pytest.raises(Exception):
            async with db.session() as s:
                await s.execute(text("SELECT 1"))
                raise RuntimeError("test rollback")

    async def test_pragmas_applied(self, db: Database) -> None:
        async with db.session() as s:
            fk = await s.execute(text("PRAGMA foreign_keys"))
            assert fk.scalar() == 1
            # In-memory SQLite always reports 'memory' for journal_mode
            # (WAL is applied but overridden by the :memory: URL).
            # Verify the PRAGMA executed without error — the important assertion
            # for production is that foreign_keys=ON is enforced.
            jm = await s.execute(text("PRAGMA journal_mode"))
            assert jm.scalar() in ("wal", "memory")

    async def test_in_memory_no_tables_before_init(self) -> None:
        d = Database(path=":memory:")
        # Don't call init — no tables yet
        async with d.session() as s:
            result = await s.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            names = [r[0] for r in result.fetchall()]
        assert names == []
        await d.close()
