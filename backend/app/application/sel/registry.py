"""
Application: Service Registry — register, discover, and persist service descriptors.

The SEL's NRF analog: every capability is registered here at startup,
persisted to the `services` table, and discoverable by agents and the UI.

Implements the ServiceRegistry domain port (domain/services/ports.py).
Owning docs: 08-services.md §6
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select

from app.domain.services.models import (
    Pattern,
    ServiceDescriptor,
    ServiceKind,
)
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import ServiceRow
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    In-memory + persisted service registry.

    Descriptors are declared in code (application/sel/services/*) and
    registered at startup.  They are also persisted to the `services` table
    so the REST /services endpoint and the UI can list them without
    importing application code.

    Startup reconciliation: re-registers from code on every boot so the
    DB is never stale.
    """

    def __init__(self, db: Database, writer: PersistenceWriter) -> None:
        self._db = db
        self._writer = writer
        self._registry: dict[str, ServiceDescriptor] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, descriptor: ServiceDescriptor) -> None:
        """Register in memory (idempotent by name)."""
        self._registry[descriptor.name] = descriptor

    async def persist_all(self) -> None:
        """Persist all in-memory descriptors to the `services` table."""
        now = datetime.now(UTC).isoformat()
        for desc in self._registry.values():
            await self._persist_one(desc, now)

    async def _persist_one(
        self, desc: ServiceDescriptor, ts: str
    ) -> None:
        row: dict[str, Any] = {
            "name": desc.name,
            "kind": desc.kind.value,
            "pattern": desc.pattern.value,
            "owner_nf": desc.owner_nf,
            "input_schema_json": "{}",
            "output_schema_json": "{}",
            "policy_tags_json": json.dumps(list(desc.policy_tags)),
            "spec_ref": desc.spec_ref,
            "approximates_operation": desc.approximates_operation,
            "idempotent": 1 if desc.idempotent else 0,
            "compensation": desc.compensation,
            "description": desc.description,
            "registered_at": ts,
        }
        await self._writer.submit(WriteOp(
            stmt=insert(ServiceRow).prefix_with("OR REPLACE").values(**row)
        ))

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def get(self, name: str) -> ServiceDescriptor | None:
        return self._registry.get(name)

    def list_services(
        self,
        kind: str | None = None,
        owner_nf: str | None = None,
        tag: str | None = None,
    ) -> list[ServiceDescriptor]:
        results = list(self._registry.values())
        if kind:
            results = [d for d in results if d.kind.value == kind]
        if owner_nf:
            results = [d for d in results if d.owner_nf == owner_nf]
        if tag:
            results = [d for d in results if d.has_tag(tag)]
        return results

    def all(self) -> list[ServiceDescriptor]:
        return list(self._registry.values())

    # ------------------------------------------------------------------
    # Async load (from DB — for reconstructing state after restart)
    # ------------------------------------------------------------------
    async def load_from_db(self) -> None:
        """Load any DB-persisted descriptors not yet in memory."""
        async with self._db.session() as s:
            result = await s.execute(select(ServiceRow))
            rows = result.scalars().all()
        for row in rows:
            if str(row.name) not in self._registry:
                try:
                    tags = tuple(json.loads(str(row.policy_tags_json or "[]")))
                    desc = ServiceDescriptor(
                        name=str(row.name),
                        kind=ServiceKind(str(row.kind)),
                        pattern=Pattern(str(row.pattern)),
                        owner_nf=str(row.owner_nf),
                        policy_tags=tags,
                        spec_ref=str(row.spec_ref or ""),
                        approximates_operation=str(
                            row.approximates_operation or ""
                        ),
                        idempotent=bool(row.idempotent),
                        compensation=str(row.compensation)
                        if row.compensation
                        else None,
                        description=str(row.description or ""),
                    )
                    self._registry[desc.name] = desc
                except Exception:
                    logger.warning("Could not reconstruct descriptor for %s", row.name)

    @property
    def count(self) -> int:
        return len(self._registry)
