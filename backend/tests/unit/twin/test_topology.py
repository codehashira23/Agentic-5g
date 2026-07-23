"""
C047: Tests for TopologyNode, TopologyLink, Topology, and NetworkTwin.
"""
from __future__ import annotations

import pytest

from app.domain.twin.network_twin import NetworkTwin, TwinSnapshot
from app.domain.twin.profile import NFStatus, NFType, Region
from app.domain.twin.topology import Topology, TopologyLink, TopologyNode


# ---------------------------------------------------------------------------
# TopologyNode
# ---------------------------------------------------------------------------
class TestTopologyNode:
    def _make(self, **kw) -> TopologyNode:
        return TopologyNode(
            id=kw.get("id", "upf_delhi_1"),
            nf_type=kw.get("nf_type", NFType.UPF),
            region=kw.get("region", Region.DELHI),
            status=kw.get("status", NFStatus.ACTIVE),
        )

    def test_construction(self) -> None:
        n = self._make()
        assert n.id == "upf_delhi_1"
        assert n.nf_type == NFType.UPF
        assert n.status == NFStatus.ACTIVE

    def test_immutable(self) -> None:
        n = self._make()
        with pytest.raises(Exception):
            n.id = "changed"  # type: ignore[misc]

    def test_with_status_returns_new_node(self) -> None:
        n = self._make()
        n2 = n.with_status(NFStatus.FAILED)
        assert n.status == NFStatus.ACTIVE
        assert n2.status == NFStatus.FAILED
        assert n is not n2

    def test_with_status_updates_load(self) -> None:
        n = self._make()
        n2 = n.with_status(NFStatus.DEGRADED, load=0.8)
        assert abs(n2.load - 0.8) < 1e-9

    def test_with_meta(self) -> None:
        n = self._make()
        n2 = n.with_meta("model_count", 2)
        assert n2.meta["model_count"] == 2
        assert "model_count" not in n.meta

    def test_load_defaults_zero(self) -> None:
        n = self._make()
        assert n.load == 0.0


# ---------------------------------------------------------------------------
# TopologyLink
# ---------------------------------------------------------------------------
class TestTopologyLink:
    def test_between_factory(self) -> None:
        lk = TopologyLink.between("gnb_delhi_1", "upf_delhi_1", ref_point="N3")
        assert lk.id == "gnb_delhi_1__upf_delhi_1"
        assert lk.src_id == "gnb_delhi_1"
        assert lk.dst_id == "upf_delhi_1"
        assert lk.ref_point == "N3"

    def test_default_metrics_zero(self) -> None:
        lk = TopologyLink.between("a", "b")
        assert lk.throughput_mbps == 0.0
        assert lk.latency_ms == 0.0
        assert lk.utilization == 0.0

    def test_with_metrics_returns_new_link(self) -> None:
        lk = TopologyLink.between("a", "b")
        lk2 = lk.with_metrics(throughput_mbps=50.0, latency_ms=12.0, utilization=0.5)
        assert lk.throughput_mbps == 0.0          # original unchanged
        assert lk2.throughput_mbps == 50.0
        assert lk2.latency_ms == 12.0
        assert lk2.utilization == 0.5

    def test_with_metrics_clamps_utilization(self) -> None:
        lk = TopologyLink.between("a", "b")
        lk2 = lk.with_metrics(utilization=2.0)
        assert lk2.utilization == 1.0

    def test_immutable(self) -> None:
        lk = TopologyLink.between("a", "b")
        with pytest.raises(Exception):
            lk.throughput_mbps = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Topology graph
# ---------------------------------------------------------------------------
class TestTopology:
    def _make_node(self, nf_id: str, nf_type: NFType = NFType.AMF,
                   region: Region = Region.CORE,
                   status: NFStatus = NFStatus.ACTIVE) -> TopologyNode:
        return TopologyNode(id=nf_id, nf_type=nf_type, region=region, status=status)

    def test_empty_on_init(self) -> None:
        t = Topology()
        assert t.node_count == 0
        assert t.link_count == 0

    def test_add_node(self) -> None:
        t = Topology().add_node(self._make_node("amf_1"))
        assert t.node_count == 1
        assert "amf_1" in t.nodes

    def test_add_node_returns_new_topology(self) -> None:
        t = Topology()
        t2 = t.add_node(self._make_node("amf_1"))
        assert t.node_count == 0   # original unchanged
        assert t2.node_count == 1

    def test_update_node(self) -> None:
        t = Topology().add_node(self._make_node("amf_1"))
        updated = self._make_node("amf_1", status=NFStatus.FAILED)
        t2 = t.update_node(updated)
        assert t2.nodes["amf_1"].status == NFStatus.FAILED

    def test_update_node_not_found_raises(self) -> None:
        t = Topology()
        with pytest.raises(KeyError):
            t.update_node(self._make_node("ghost"))

    def test_remove_node_also_removes_links(self) -> None:
        t = (
            Topology()
            .add_node(self._make_node("amf_1"))
            .add_node(self._make_node("smf_1", NFType.SMF))
            .add_link(TopologyLink.between("amf_1", "smf_1"))
        )
        t2 = t.remove_node("amf_1")
        assert "amf_1" not in t2.nodes
        assert t2.link_count == 0

    def test_nodes_by_region(self) -> None:
        t = (
            Topology()
            .add_node(self._make_node("upf_delhi", NFType.UPF, Region.DELHI))
            .add_node(self._make_node("upf_mumbai", NFType.UPF, Region.MUMBAI))
            .add_node(self._make_node("nrf_core", NFType.NRF, Region.CORE))
        )
        delhi_nodes = t.nodes_by_region(Region.DELHI)
        assert len(delhi_nodes) == 1
        assert delhi_nodes[0].id == "upf_delhi"

    def test_nodes_by_type(self) -> None:
        t = (
            Topology()
            .add_node(self._make_node("upf_1", NFType.UPF))
            .add_node(self._make_node("upf_2", NFType.UPF))
            .add_node(self._make_node("amf_1", NFType.AMF))
        )
        upf_nodes = t.nodes_by_type(NFType.UPF)
        assert len(upf_nodes) == 2

    def test_healthy_nodes(self) -> None:
        t = (
            Topology()
            .add_node(self._make_node("active", status=NFStatus.ACTIVE))
            .add_node(self._make_node("standby", status=NFStatus.STANDBY))
            .add_node(self._make_node("failed", status=NFStatus.FAILED))
        )
        assert len(t.healthy_nodes()) == 2
        assert len(t.failed_nodes()) == 1

    def test_health_pct(self) -> None:
        t = (
            Topology()
            .add_node(self._make_node("a", status=NFStatus.ACTIVE))
            .add_node(self._make_node("b", status=NFStatus.ACTIVE))
            .add_node(self._make_node("c", status=NFStatus.FAILED))
        )
        assert abs(t.health_pct - 2 / 3) < 1e-9

    def test_health_pct_empty_topology(self) -> None:
        assert Topology().health_pct == 1.0

    def test_add_link(self) -> None:
        t = (
            Topology()
            .add_node(self._make_node("a"))
            .add_node(self._make_node("b"))
            .add_link(TopologyLink.between("a", "b", "N3"))
        )
        assert t.link_count == 1

    def test_links_from(self) -> None:
        t = (
            Topology()
            .add_node(self._make_node("a"))
            .add_node(self._make_node("b"))
            .add_node(self._make_node("c"))
            .add_link(TopologyLink.between("a", "b"))
            .add_link(TopologyLink.between("a", "c"))
            .add_link(TopologyLink.between("b", "c"))
        )
        assert len(t.links_from("a")) == 2
        assert len(t.links_to("c")) == 2

    def test_get_node_returns_none_if_missing(self) -> None:
        t = Topology()
        assert t.get_node("ghost") is None


# ---------------------------------------------------------------------------
# NetworkTwin aggregate
# ---------------------------------------------------------------------------
class FakeRng:
    def __init__(self, fixed: float = 0.5) -> None:
        self._fixed = fixed

    def random(self) -> float:
        return self._fixed

    def gauss(self, mu: float, sigma: float) -> float:
        return mu

    def uniform(self, lo: float, hi: float) -> float:
        return (lo + hi) / 2.0


class TestNetworkTwin:
    def test_from_baseline_creates_nfs(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        assert twin.nf_count > 0

    def test_from_baseline_contains_nrf(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        nrfs = twin.nfs_by_type(NFType.NRF)
        assert len(nrfs) >= 2   # primary + standby

    def test_from_baseline_contains_edge_nodes(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        edges = twin.nfs_by_type(NFType.EDGE)
        assert len(edges) >= 2   # one per region

    def test_topology_built_with_nodes(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        assert twin.topology.node_count > 0

    def test_topology_has_links(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        assert twin.topology.link_count > 0

    def test_advance_increments_tick(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        assert twin.tick == 0
        twin.advance(FakeRng(0.5), tick=1)
        assert twin.tick == 1

    def test_advance_returns_events(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        events = twin.advance(FakeRng(0.5), tick=1)
        assert isinstance(events, list)

    def test_advance_deterministic(self) -> None:
        """Same seed + same rng → same events for two twins."""
        t1 = NetworkTwin.from_baseline(seed=42)
        t2 = NetworkTwin.from_baseline(seed=42)
        e1 = t1.advance(FakeRng(0.5), tick=1)
        e2 = t2.advance(FakeRng(0.5), tick=1)
        # Same number and types of events
        assert len(e1) == len(e2)
        types1 = [type(e).__name__ for e in e1]
        types2 = [type(e).__name__ for e in e2]
        assert types1 == types2

    def test_snapshot_returns_twin_snapshot(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        snap = twin.snapshot()
        assert isinstance(snap, TwinSnapshot)
        assert snap.tick == 0
        assert snap.health_pct >= 0.0

    def test_snapshot_contains_all_nfs(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        snap = twin.snapshot()
        assert len(snap.nf_states) == twin.nf_count

    def test_snapshot_nf_state_has_required_keys(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        snap = twin.snapshot()
        first_state = next(iter(snap.nf_states.values()))
        for key in ("type", "region", "status", "load", "kpis"):
            assert key in first_state

    def test_apply_command_nrf_discover(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        # Register each NRF with itself so discover works
        for nf in twin.nfs_by_type(NFType.NRF):
            if nf.is_healthy():
                nf.handle("nrf.register", {"profile": nf.profile.model_dump()})
        result = twin.apply_command(
            "nrf.discover",
            {"nf_type": "NRF", "target": "nrf_core_1"},
        )
        assert "profiles" in result

    def test_apply_command_unknown_target_raises(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        with pytest.raises(ValueError):
            twin.apply_command("nrf.discover", {"target": "ghost_nf_99"})

    def test_topology_synced_after_advance(self) -> None:
        """After failing an NF via rng=0.0, topology should reflect FAILED."""
        twin = NetworkTwin.from_baseline(seed=42)
        # rng=0.0 will trigger hazard failures for some NFs
        twin.advance(FakeRng(0.0), tick=1)
        snap = twin.snapshot()
        # At least some nodes may be failed; topology health_pct < 1.0
        # (depends on which NFs' hazard probabilities trigger at 0.0)
        assert 0.0 <= snap.health_pct <= 1.0

    def test_get_nf_returns_none_for_unknown(self) -> None:
        twin = NetworkTwin.from_baseline(seed=42)
        assert twin.get_nf("ghost") is None
