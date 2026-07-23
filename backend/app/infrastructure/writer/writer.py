"""
Infrastructure: Single-writer persistence queue.

Serialises ALL SQLite writes through one asyncio queue so SQLite's
"database is locked" error never fires under concurrent coroutines
(10-backend.md §8.2, ADR-5).

Two submission modes:
  submit()       — write-through: queued immediately, committed promptly.
                   Used for events, service_calls, command mutations.
  submit_batch() — write-behind: caller provides a list; flushed together
                   with regular items. Used for high-frequency KPI samples.

The `run()` coroutine is started as a background task in the lifespan
(10-backend.md §5) and drains the queue in bounded batches.
On shutdown (close()) the queue is fully drained so no rows are lost.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.infrastructure.db.engine import Database


# ---------------------------------------------------------------------------
# WriteOp — a single pending write operation
# ---------------------------------------------------------------------------
@dataclass
class WriteOp:
    """One pending database operation (INSERT or UPDATE)."""
    stmt: Any              # SQLAlchemy Insert / Update statement
    values: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PersistenceWriter
# ---------------------------------------------------------------------------
class PersistenceWriter:
    """
    Single-writer queue for SQLite writes.

    Usage (background task):
        writer = PersistenceWriter(db)
        asyncio.create_task(writer.run())   # started in lifespan
        ...
        await writer.submit(WriteOp(stmt, values))
        ...
        await writer.close()   # drains + stops
    """

    MAX_BATCH = 200        # max ops committed per cycle
    DRAIN_TIMEOUT = 0.05   # seconds between drain attempts when idle

    def __init__(self, db: Database) -> None:
        self._db = db
        self._queue: asyncio.Queue[WriteOp | None] = asyncio.Queue()
        self._running = False
        self._total_written = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def submit(self, op: WriteOp) -> None:
        """Queue one write-through operation."""
        await self._queue.put(op)

    async def submit_many(self, ops: list[WriteOp]) -> None:
        """Queue multiple operations (write-behind batch)."""
        for op in ops:
            await self._queue.put(op)

    # ------------------------------------------------------------------
    # Background task
    # ------------------------------------------------------------------
    async def run(self) -> None:
        """
        Drain loop — runs until close() is called.
        Commits in batches of up to MAX_BATCH ops.
        """
        self._running = True
        while self._running:
            batch = await self._drain(self.MAX_BATCH)
            if batch:
                await self._commit(batch)
            else:
                await asyncio.sleep(self.DRAIN_TIMEOUT)

        # Final drain after stop signal
        remaining: list[WriteOp] = []
        while not self._queue.empty():
            item = self._queue.get_nowait()
            if item is not None:
                remaining.append(item)
        if remaining:
            await self._commit(remaining)

    async def close(self) -> None:
        """Signal the run loop to stop and flush all pending writes."""
        self._running = False
        await self._queue.put(None)   # wake up a sleeping drain loop

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    @property
    def total_written(self) -> int:
        return self._total_written

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _drain(self, max_n: int) -> list[WriteOp]:
        """Pull up to max_n ops from the queue (non-blocking after first)."""
        batch: list[WriteOp] = []
        try:
            # Wait for at least one item
            first = await asyncio.wait_for(self._queue.get(), timeout=self.DRAIN_TIMEOUT)
            if first is None:
                return batch   # stop sentinel
            batch.append(first)
        except TimeoutError:
            return batch

        # Grab remaining without blocking
        while len(batch) < max_n:
            try:
                item = self._queue.get_nowait()
                if item is None:
                    break
                batch.append(item)
            except asyncio.QueueEmpty:
                break
        return batch

    async def _commit(self, batch: list[WriteOp]) -> None:
        """Execute all ops in a single transaction."""
        async with self._db.engine.begin() as conn:
            for op in batch:
                if op.values:
                    await conn.execute(op.stmt, op.values)
                else:
                    await conn.execute(op.stmt)
        self._total_written += len(batch)
