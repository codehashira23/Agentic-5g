"""
Analytics router — KPI time-series queries for the Analytics page.
GET /analytics/kpis  — returns recent KPI samples for a node
GET /analytics/nodes — returns list of nodes that have KPI data
Owning docs: 09-api.md §9.10
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, text

from app.api.deps import get_container
from app.infrastructure.container import Container
from app.infrastructure.db.models import KpiRow, TopologyNodeRow

router = APIRouter()


@router.get("/kpis")
async def get_kpis(
    node_id: str,
    kpi: str = "latency_ms",
    limit: int = 100,
    c: Container = Depends(get_container),
) -> list[dict]:
    """Return recent KPI samples for a given node and KPI name."""
    async with c.db.session() as session:
        result = await session.execute(
            select(KpiRow)
            .where(KpiRow.node_id == node_id)
            .where(KpiRow.kpi == kpi)
            .order_by(text("tick DESC"))
            .limit(limit)
        )
        rows = result.scalars().all()
    # Return in ascending tick order for the chart
    return [
        {"tick": r.tick, "value": round(r.value, 3), "ts": r.ts}
        for r in reversed(rows)
    ]


@router.get("/nodes")
async def get_kpi_nodes(
    c: Container = Depends(get_container),
) -> list[dict]:
    """Return all node IDs that have KPI data, with their type and region."""
    async with c.db.session() as session:
        # Get distinct node_ids from kpis table
        kpi_result = await session.execute(
            select(KpiRow.node_id).distinct()
        )
        node_ids = {r for r in kpi_result.scalars().all()}

        # Get node metadata from topology_nodes
        node_result = await session.execute(
            select(TopologyNodeRow).where(TopologyNodeRow.id.in_(node_ids))
        )
        nodes = node_result.scalars().all()

    return [
        {"id": n.id, "type": n.type, "region": n.region}
        for n in sorted(nodes, key=lambda x: (x.region, x.type, x.id))
    ]


@router.get("/kpis/available")
async def get_available_kpis(
    node_id: str,
    c: Container = Depends(get_container),
) -> list[str]:
    """Return distinct KPI names available for a node."""
    async with c.db.session() as session:
        result = await session.execute(
            select(KpiRow.kpi).distinct().where(KpiRow.node_id == node_id)
        )
        return sorted(result.scalars().all())
