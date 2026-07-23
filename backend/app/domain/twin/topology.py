"""
Domain: Topology — nodes, links, regions, and the full network graph.

Defines:
  - TopologyNode  : a node in the topology graph (wraps an NF id + metadata)
  - TopologyLink  : a directed link between two nodes with live metrics
  - Topology      : the complete graph (nodes + links) with query helpers

Rules:
  - Pure Python + Pydantic only. Zero framework imports.
  - Immutable value objects where the graph structure is fixed;
    link metrics are updated via functional copy.
  - Topology is the source of truth for the React Flow canvas (04-ui.md §9.3).

Owning docs: 06-digital-twin.md §6, 07-network-core.md §5
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.twin.profile import NFStatus, NFType, Region


# ---------------------------------------------------------------------------
# TopologyNode
# ---------------------------------------------------------------------------
class TopologyNode(BaseModel):
    """A node in the network topology graph."""

    model_config = {"frozen": True}

    id: str = Field(..., description="Matches the NF/entity id, e.g. 'upf_delhi_1'")
    nf_type: NFType
    region: Region
    status: NFStatus = NFStatus.ACTIVE
    load: float = Field(default=0.0, ge=0.0, le=1.0)

    # Layout coordinates for the React Flow canvas (04-ui.md §9.3)
    x: float = 0.0
    y: float = 0.0

    # Extra role-specific display data (e.g. model badges for Edge nodes)
    meta: dict[str, Any] = Field(default_factory=dict)

    def with_status(self, status: NFStatus, load: float | None = None) -> TopologyNode:
        """Return a new node with updated status/load (immutable update)."""
        updates: dict[str, Any] = {"status": status}
        if load is not None:
            updates["load"] = max(0.0, min(1.0, load))
        return self.model_copy(update=updates)

    def with_meta(self, key: str, value: Any) -> TopologyNode:
        """Return a new node with a meta key set (immutable update)."""
        new_meta = {**self.meta, key: value}
        return self.model_copy(update={"meta": new_meta})


# ---------------------------------------------------------------------------
# TopologyLink
# ---------------------------------------------------------------------------
class TopologyLink(BaseModel):
    """A directed link between two topology nodes with live metrics."""

    model_config = {"frozen": True}

    id: str = Field(..., description="Unique link id, e.g. 'gnb_delhi_1__upf_delhi_1'")
    src_id: str
    dst_id: str
    ref_point: str = Field(
        default="",
        description="3GPP reference point, e.g. 'N3', 'N4', 'N6'",
    )

    # Live metrics (updated each tick via functional copy)
    throughput_mbps: float = 0.0
    latency_ms: float = 0.0
    utilization: float = Field(default=0.0, ge=0.0, le=1.0)

    def with_metrics(
        self,
        throughput_mbps: float | None = None,
        latency_ms: float | None = None,
        utilization: float | None = None,
    ) -> TopologyLink:
        updates: dict[str, Any] = {}
        if throughput_mbps is not None:
            updates["throughput_mbps"] = max(0.0, throughput_mbps)
        if latency_ms is not None:
            updates["latency_ms"] = max(0.0, latency_ms)
        if utilization is not None:
            updates["utilization"] = max(0.0, min(1.0, utilization))
        return self.model_copy(update=updates)

    @classmethod
    def between(
        cls,
        src_id: str,
        dst_id: str,
        ref_point: str = "",
    ) -> TopologyLink:
        """Factory: create a link with auto-generated id."""
        return cls(
            id=f"{src_id}__{dst_id}",
            src_id=src_id,
            dst_id=dst_id,
            ref_point=ref_point,
        )


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------
class Topology(BaseModel):
    """
    The complete network topology graph.

    Stored as dicts (keyed by id) for O(1) lookups.
    Mutated via functional update methods — returns new Topology instances.
    """

    nodes: dict[str, TopologyNode] = Field(default_factory=dict)
    links: dict[str, TopologyLink] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Node helpers
    # ------------------------------------------------------------------
    def add_node(self, node: TopologyNode) -> Topology:
        return Topology(
            nodes={**self.nodes, node.id: node},
            links=self.links,
        )

    def update_node(self, node: TopologyNode) -> Topology:
        """Replace an existing node; raises KeyError if not found."""
        if node.id not in self.nodes:
            raise KeyError(f"Node '{node.id}' not in topology")
        return self.add_node(node)

    def remove_node(self, node_id: str) -> Topology:
        new_nodes = {k: v for k, v in self.nodes.items() if k != node_id}
        # Also remove all links connected to this node
        new_links = {
            k: v for k, v in self.links.items()
            if v.src_id != node_id and v.dst_id != node_id
        }
        return Topology(nodes=new_nodes, links=new_links)

    def get_node(self, node_id: str) -> TopologyNode | None:
        return self.nodes.get(node_id)

    def nodes_by_region(self, region: Region) -> list[TopologyNode]:
        return [n for n in self.nodes.values() if n.region == region]

    def nodes_by_type(self, nf_type: NFType) -> list[TopologyNode]:
        return [n for n in self.nodes.values() if n.nf_type == nf_type]

    def healthy_nodes(self) -> list[TopologyNode]:
        return [
            n for n in self.nodes.values()
            if n.status in (NFStatus.ACTIVE, NFStatus.STANDBY)
        ]

    def failed_nodes(self) -> list[TopologyNode]:
        return [n for n in self.nodes.values() if n.status == NFStatus.FAILED]

    # ------------------------------------------------------------------
    # Link helpers
    # ------------------------------------------------------------------
    def add_link(self, link: TopologyLink) -> Topology:
        return Topology(
            nodes=self.nodes,
            links={**self.links, link.id: link},
        )

    def update_link(self, link: TopologyLink) -> Topology:
        if link.id not in self.links:
            raise KeyError(f"Link '{link.id}' not in topology")
        return self.add_link(link)

    def links_from(self, node_id: str) -> list[TopologyLink]:
        return [lk for lk in self.links.values() if lk.src_id == node_id]

    def links_to(self, node_id: str) -> list[TopologyLink]:
        return [lk for lk in self.links.values() if lk.dst_id == node_id]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def link_count(self) -> int:
        return len(self.links)

    @property
    def health_pct(self) -> float:
        """Fraction of nodes that are healthy (0-1)."""
        if not self.nodes:
            return 1.0
        return len(self.healthy_nodes()) / len(self.nodes)
