"""
Infrastructure: Async SQLite engine with performance and safety PRAGMAs.

PRAGMAs applied on every connection (10-backend.md §8.1):
  journal_mode=WAL  — concurrent reads while writing; better throughput
  foreign_keys=ON   — enforce FK constraints (SQLite ignores them by default)
  busy_timeout=5000 — wait up to 5 s before raising "database is locked"
  synchronous=NORMAL— safe durability with better write throughput than FULL

All writes go through the single-writer queue (C064); reads use short-lived
sessions produced by `session_scope()`.

Owning docs: 10-backend.md §8.1, 12-database.md §4
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# ORM declarative base — all ORM model classes inherit from this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Database — wraps the engine, session factory, and schema creation
# ---------------------------------------------------------------------------
class Database:
    """
    Manages the async SQLite engine and session factory.

    Usage:
        db = Database(path=Path("data/agent5g.db"))
        await db.init()          # create tables if absent
        async with db.session() as s:
            result = await s.execute(...)
    """

    def __init__(self, path: Path | str = ":memory:") -> None:
        url = (
            "sqlite+aiosqlite:///:memory:"
            if str(path) == ":memory:"
            else f"sqlite+aiosqlite:///{path}"
        )
        self._engine: AsyncEngine = create_async_engine(
            url,
            echo=False,
            future=True,
            # SQLite serialises writes internally; pool_size not meaningful
            connect_args={"check_same_thread": False},
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        # Apply PRAGMAs on every new connection
        self._register_pragmas()

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------
    async def init(self) -> None:
        """Create all tables declared via Base metadata (idempotent)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all(self) -> None:
        """Drop all tables — test/reset use only."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    # ------------------------------------------------------------------
    # Session context manager — for short-lived reads
    # ------------------------------------------------------------------
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope for reads.
        Commits on clean exit, rolls back on exception.
        All writes should go through the single-writer queue (C064).
        """
        async with self._session_factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    # ------------------------------------------------------------------
    # Low-level write access (used by the single-writer queue)
    # ------------------------------------------------------------------
    async def execute_write(self, stmt: Any, params: dict | None = None) -> None:
        """Execute a single write statement outside the session factory."""
        async with self._engine.begin() as conn:
            if params:
                await conn.execute(stmt, params)
            else:
                await conn.execute(stmt)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def close(self) -> None:
        await self._engine.dispose()

    # ------------------------------------------------------------------
    # PRAGMA registration
    # ------------------------------------------------------------------
    def _register_pragmas(self) -> None:
        """
        Register a synchronous listener that fires for every new
        raw DBAPI connection and applies the required PRAGMAs.
        SQLAlchemy's `@event.listens_for` works with the sync DBAPI
        connection even when using the async engine.
        """
        @event.listens_for(self._engine.sync_engine, "connect")
        def _apply_pragmas(dbapi_conn: object, _: object) -> None:
            cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
