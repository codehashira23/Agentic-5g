"""C064: Tests for the single-writer persistence queue."""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text

from app.infrastructure.db.engine import Database
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp


@pytest.fixture
async def db() -> Database:
    d = Database(":memory:")
    await d.init()
    yield d
    await d.close()


@pytest.fixture
def writer(db: Database) -> PersistenceWriter:
    return PersistenceWriter(db)


class TestWriterBasic:
    async def test_submit_and_flush(self, db: Database, writer: PersistenceWriter) -> None:
        """Items submitted are committed after run() drains."""
        # Create a simple table to write into
        async with db.engine.begin() as conn:
            await conn.execute(text("CREATE TABLE IF NOT EXISTS t (v INTEGER)"))

        await writer.submit(WriteOp(stmt=text("INSERT INTO t VALUES (:v)"),
                                    values={"v": 42}))

        # Run one drain cycle manually (no background task needed in tests)
        batch = await writer._drain(200)
        await writer._commit(batch)

        async with db.session() as s:
            result = await s.execute(text("SELECT v FROM t"))
            assert result.scalar() == 42

    async def test_total_written_increments(self, db: Database, writer: PersistenceWriter) -> None:
        async with db.engine.begin() as conn:
            await conn.execute(text("CREATE TABLE IF NOT EXISTS t2 (v INTEGER)"))

        ops = [WriteOp(text("INSERT INTO t2 VALUES (:v)"), {"v": i}) for i in range(5)]
        await writer.submit_many(ops)
        batch = await writer._drain(200)
        await writer._commit(batch)
        assert writer.total_written == 5

    async def test_queue_size_increases(self, writer: PersistenceWriter) -> None:
        for i in range(3):
            await writer.submit(WriteOp(text("SELECT 1")))
        assert writer.queue_size == 3

    async def test_drain_returns_empty_when_idle(self, writer: PersistenceWriter) -> None:
        batch = await writer._drain(200)
        assert batch == []

    async def test_submit_many_queues_all(self, writer: PersistenceWriter) -> None:
        ops = [WriteOp(text("SELECT 1")) for _ in range(10)]
        await writer.submit_many(ops)
        assert writer.queue_size == 10

    async def test_close_drains_remaining(self, db: Database, writer: PersistenceWriter) -> None:
        """close() must not lose enqueued writes."""
        async with db.engine.begin() as conn:
            await conn.execute(text("CREATE TABLE IF NOT EXISTS t3 (v INTEGER)"))

        await writer.submit(WriteOp(text("INSERT INTO t3 VALUES (:v)"), {"v": 99}))

        # Simulate close: stop + drain remaining
        writer._running = False
        remaining: list[WriteOp] = []
        while not writer._queue.empty():
            item = writer._queue.get_nowait()
            if item is not None:
                remaining.append(item)
        if remaining:
            await writer._commit(remaining)

        async with db.session() as s:
            result = await s.execute(text("SELECT v FROM t3"))
            assert result.scalar() == 99
