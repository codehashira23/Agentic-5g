"""Log repository — write log rows and query audit trail."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import EventRow, LogRow
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp


class LogRepository:
    """Writes structured logs and domain events; reads the audit trail."""

    def __init__(self, db: Database, writer: PersistenceWriter) -> None:
        self._db = db
        self._writer = writer

    async def append_log(
        self,
        level: str,
        message: str,
        log_type: str = "",
        correlation_id: str | None = None,
        nf: str | None = None,
        service: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        import json

        from sqlalchemy import insert
        await self._writer.submit(WriteOp(
            stmt=insert(LogRow).values(
                ts=datetime.now(UTC).isoformat(),
                level=level,
                type=log_type,
                correlation_id=correlation_id,
                nf=nf,
                service=service,
                message=message,
                payload_json=json.dumps(payload or {}),
            )
        ))

    async def append_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        entity_id: str | None = None,
        tick: int = 0,
        run_id: int | None = None,
    ) -> None:
        import json

        from sqlalchemy import insert
        await self._writer.submit(WriteOp(
            stmt=insert(EventRow).values(
                type=event_type,
                correlation_id=correlation_id,
                entity_id=entity_id,
                payload_json=json.dumps(payload),
                tick=tick,
                run_id=run_id,
                ts=datetime.now(UTC).isoformat(),
            )
        ))

    async def get_logs(
        self,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        async with self._db.session() as s:
            q = select(LogRow).order_by(LogRow.ts.desc()).limit(limit)
            if correlation_id:
                q = q.where(LogRow.correlation_id == correlation_id)
            result = await s.execute(q)
            rows = result.scalars().all()
        return [
            {"id": r.id, "ts": r.ts, "level": r.level, "message": r.message,
             "correlation_id": r.correlation_id}
            for r in rows
        ]

    async def get_events(
        self,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        async with self._db.session() as s:
            q = select(EventRow).order_by(EventRow.ts.desc()).limit(limit)
            if correlation_id:
                q = q.where(EventRow.correlation_id == correlation_id)
            result = await s.execute(q)
            rows = result.scalars().all()
        return [
            {"id": r.id, "ts": r.ts, "type": r.type,
             "entity_id": r.entity_id, "correlation_id": r.correlation_id}
            for r in rows
        ]
