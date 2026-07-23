"""Memory store — persist/retrieve agent memory and knowledge graph."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select

from app.domain.agents.memory import KnowledgeEdge, KnowledgeNode, MemoryRecord
from app.domain.agents.models import MemoryScope
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import KnowledgeEdgeRow, KnowledgeNodeRow, MemoryRow
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp


class SqlMemoryStore:
    def __init__(self, db: Database, writer: PersistenceWriter) -> None:
        self._db = db
        self._writer = writer

    # --- Records ---
    async def save_record(self, record: MemoryRecord) -> None:
        row: dict[str, Any] = {
            "id": record.id,
            "scope": record.scope.value,
            "content_json": json.dumps(record.content),
            "summary": record.summary,
            "workflow_id": record.provenance_workflow_id,
            # created_by_agent intentionally omitted — FK to agents.role
            # is only valid after seeding; default value in DB handles it
            "weight": record.weight,
            "created_at": record.created_at.isoformat(),
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        }
        await self._writer.submit(WriteOp(
            stmt=insert(MemoryRow).prefix_with("OR REPLACE").values(**row)
        ))

    async def get_records(
        self, scope: MemoryScope, limit: int = 20,
        workflow_id: str | None = None,
    ) -> list[MemoryRecord]:
        async with self._db.session() as s:
            q = (select(MemoryRow)
                 .where(MemoryRow.scope == scope.value)
                 .order_by(MemoryRow.created_at.desc())
                 .limit(limit))
            if workflow_id:
                q = q.where(MemoryRow.workflow_id == workflow_id)
            result = await s.execute(q)
            rows = result.scalars().all()
        return [self._record_from_row(r) for r in rows]

    async def get_record(self, record_id: str) -> MemoryRecord | None:
        async with self._db.session() as s:
            row = await s.get(MemoryRow, record_id)
        return self._record_from_row(row) if row else None

    # --- Knowledge graph ---
    async def upsert_node(self, node: KnowledgeNode) -> None:
        row: dict[str, Any] = {
            "id": node.id,
            "entity_type": node.entity_type,
            "label": node.label,
            "props_json": json.dumps(node.props),
            "first_seen_at": node.first_seen_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
        }
        await self._writer.submit(WriteOp(
            stmt=insert(KnowledgeNodeRow).prefix_with("OR REPLACE").values(**row)
        ))

    async def upsert_edge(self, edge: KnowledgeEdge) -> None:
        row: dict[str, Any] = {
            "src_id": edge.src_id,
            "relation": edge.relation,
            "dst_id": edge.dst_id,
            "props_json": json.dumps(edge.props),
            "provenance_workflow_id": edge.provenance_workflow_id,
            "created_at": edge.created_at.isoformat(),
        }
        await self._writer.submit(WriteOp(
            stmt=insert(KnowledgeEdgeRow).values(**row)
        ))

    async def get_neighbourhood(
        self, node_id: str, depth: int = 1,
    ) -> dict[str, Any]:
        async with self._db.session() as s:
            src_q = select(KnowledgeEdgeRow).where(KnowledgeEdgeRow.src_id == node_id)
            dst_q = select(KnowledgeEdgeRow).where(KnowledgeEdgeRow.dst_id == node_id)
            edges_out = (await s.execute(src_q)).scalars().all()
            edges_in = (await s.execute(dst_q)).scalars().all()
        return {
            "node_id": node_id,
            "edges_out": [{"relation": e.relation, "dst": e.dst_id} for e in edges_out],
            "edges_in": [{"relation": e.relation, "src": e.src_id} for e in edges_in],
        }

    @staticmethod
    def _record_from_row(row: MemoryRow) -> MemoryRecord:
        return MemoryRecord(
            id=str(row.id),
            scope=MemoryScope(str(row.scope)),
            content=json.loads(str(row.content_json or "{}")),
            summary=str(row.summary),
            provenance_workflow_id=str(row.workflow_id) if row.workflow_id else None,
            created_by_agent=str(row.created_by_agent or "memory"),
            weight=float(row.weight),
            created_at=datetime.fromisoformat(str(row.created_at)),
            expires_at=datetime.fromisoformat(str(row.expires_at)) if row.expires_at else None,
        )
