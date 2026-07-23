"""Topology router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.infrastructure.container import Container

router = APIRouter()


@router.get("")
async def get_topology(
    region: str | None = None,
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    snap = c.twin_service.snapshot()
    topo = snap.topology
    nodes = list(topo.nodes.values())
    links = list(topo.links.values())
    if region:
        node_ids = {n.id for n in nodes if n.region.value == region}
        nodes = [n for n in nodes if n.id in node_ids]
        links = [lk for lk in links
                 if lk.src_id in node_ids or lk.dst_id in node_ids]
    return {
        "nodes": [
            {"id": n.id, "type": n.nf_type.value,
             "region": n.region.value, "status": n.status.value,
             "load": n.load, "x": n.x, "y": n.y}
            for n in nodes
        ],
        "links": [
            {"id": lk.id, "src_id": lk.src_id, "dst_id": lk.dst_id,
             "ref_point": lk.ref_point, "latency_ms": lk.latency_ms,
             "throughput_mbps": lk.throughput_mbps}
            for lk in links
        ],
        "regions": list({n.region.value for n in topo.nodes.values()}),
    }
