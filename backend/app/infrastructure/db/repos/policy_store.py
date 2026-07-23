"""Policy store — load and persist policy configuration."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select

from app.domain.services.policy import Policy, PolicyDecision, PolicySeverity
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import PolicyRow
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp


class SqlPolicyStore:
    def __init__(self, db: Database, writer: PersistenceWriter) -> None:
        self._db = db
        self._writer = writer

    async def load_all(self) -> list[Policy]:
        async with self._db.session() as s:
            result = await s.execute(select(PolicyRow))
            rows = result.scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, policy: Policy) -> None:
        row_data: dict[str, Any] = {
            "id": policy.id,
            "name": policy.name,
            "enabled": 1 if policy.enabled else 0,
            "severity": policy.severity.value,
            "match_json": json.dumps({
                "services": list(policy.match_services),
                "tags": list(policy.match_tags),
            }),
            "condition_ref": policy.condition_ref,
            "decision": policy.decision.value,
            "message": policy.message,
            "builtin": 1 if policy.builtin else 0,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        await self._writer.submit(WriteOp(
            stmt=insert(PolicyRow).prefix_with("OR REPLACE").values(**row_data)
        ))

    async def get(self, policy_id: str) -> Policy | None:
        async with self._db.session() as s:
            row = await s.get(PolicyRow, policy_id)
        if row is None:
            return None
        return self._to_domain(row)

    @staticmethod
    def _to_domain(row: PolicyRow) -> Policy:
        match_data = json.loads(str(row.match_json or "{}"))
        return Policy(
            id=str(row.id),
            name=str(row.name),
            enabled=bool(row.enabled),
            severity=PolicySeverity(str(row.severity)),
            match_services=tuple(match_data.get("services", [])),
            match_tags=tuple(match_data.get("tags", [])),
            decision=PolicyDecision(str(row.decision)),
            condition_ref=str(row.condition_ref),
            message=str(row.message or ""),
            builtin=bool(row.builtin),
        )
