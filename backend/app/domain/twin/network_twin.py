"""
Domain: NetworkTwin — the root aggregate of the Digital Twin.

Owns all NF entities and the topology, advances them each tick,
and produces the canonical TwinSnapshot read by agents and the UI.

Rules:
  - Pure Python only.  No Pydantic (aggregate holds mutable NF objects).
  - All randomness through the injected RngStream (GR4 / TP2).
  - advance() iterates entities in SORTED id order — deterministic (TP2).
  - External mutation only via apply_command() (TP6).
  - Returns all DomainEvents produced during a tick.

Owning docs: 06-digital-twin.md §4, §7
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.twin.entities import AdvanceContext, NetworkFunction, RngStream
from app.domain.twin.events import DomainEvent
from app.domain.twin.nf.amf import AMF
from app.domain.twin.nf.dcf import DCF
from app.domain.twin.nf.edge import EdgeNode
from app.domain.twin.nf.nrf import NRF
from app.domain.twin.nf.nwdaf import NWDAF
from app.domain.twin.nf.remaining import AF, GNB, NEF, PCF, UDM, UE
from app.domain.twin.nf.smf import SMF
from app.domain.twin.nf.upf import UPF
from app.domain.twin.profile import NFStatus, NFType, Region
from app.domain.twin.topology import Topology, TopologyLink, TopologyNode


# ---------------------------------------------------------------------------
# TwinSnapshot — the immutable read model served to agents and the UI
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TwinSnapshot:
    """Point-in-time read model of the entire twin state."""

    tick: int
    topology: Topology
    nf_states: dict[str, dict[str, Any]]   # nf_id → {status, load, kpis…}
    health_pct: float


# ---------------------------------------------------------------------------
# NetworkTwin — root aggregate
# ---------------------------------------------------------------------------
class NetworkTwin:
    """
    Root aggregate of the Digital Twin.

    Lifecycle:
      twin = NetworkTwin.from_scenario(seed, scenario_config)
      events = twin.advance(rng, tick)    # called by TwinService each tick
      snapshot = twin.snapshot()          # called by read services
      twin.apply_command(service, args)   # called by SEL invoker
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self._tick: int = 0
        self._nfs: dict[str, NetworkFunction] = {}
        self._topology: Topology = Topology()

    # ------------------------------------------------------------------
    # Factory — build a minimal "baseline_healthy" twin
    # ------------------------------------------------------------------
    @classmethod
    def from_baseline(
        cls,
        seed: int = 42,
        regions: tuple[Region, ...] = (Region.DELHI, Region.MUMBAI),
    ) -> NetworkTwin:
        """
        Build the default baseline_healthy scenario (06-digital-twin.md §16).
        Two edge regions + core NFs.
        """
        twin = cls(seed=seed)

        # --- Core NFs (region=CORE) ---
        core_nfs: list[NetworkFunction] = [
            NRF(nf_id="nrf_core_1", region=Region.CORE),
            NRF(nf_id="nrf_standby_1", region=Region.CORE,
                status=NFStatus.STANDBY, is_standby=True),
            AMF(nf_id="amf_core_1", region=Region.CORE),
            SMF(nf_id="smf_core_1", region=Region.CORE),
            UDM(nf_id="udm_core_1", region=Region.CORE),
            PCF(nf_id="pcf_core_1", region=Region.CORE),
            NWDAF(nf_id="nwdaf_core_1", region=Region.CORE),
            DCF(nf_id="dcf_core_1", region=Region.CORE),
            NEF(nf_id="nef_core_1", region=Region.CORE),
            AF(nf_id="af_core_1", region=Region.CORE),
        ]
        for nf in core_nfs:
            twin._register(nf)

        # --- Regional NFs (one set per region) ---
        for region in regions:
            r = region.value.lower()
            regional: list[NetworkFunction] = [
                UPF(nf_id=f"upf_{r}_1", region=region),
                GNB(nf_id=f"gnb_{r}_1", region=region),
                GNB(nf_id=f"gnb_{r}_2", region=region),
                EdgeNode(nf_id=f"edge_{r}_1", region=region),
            ]
            for nf in regional:
                twin._register(nf)
            # A few UEs per region
            for i in range(1, 6):
                ue = UE(nf_id=f"ue_{r}_{i:02d}", region=region)
                twin._register(ue)

        # --- Build topology ---
        twin._topology = twin._build_topology()
        return twin

    # ------------------------------------------------------------------
    # advance — the tick loop entry point (called by TwinService)
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, tick: int) -> list[DomainEvent]:
        """
        Advance every NF by one tick in sorted-id order (determinism).
        Returns all events emitted this tick.
        """
        self._tick = tick
        ctx = AdvanceContext(tick=tick, demand_factor=1.0)
        events: list[DomainEvent] = []

        for nf_id in sorted(self._nfs.keys()):
            nf = self._nfs[nf_id]
            nf_events = nf.advance(rng, ctx)
            events.extend(nf_events)

        # Sync topology node statuses from NF states
        self._sync_topology()
        return events

    # ------------------------------------------------------------------
    # snapshot — read model for agents and the UI
    # ------------------------------------------------------------------
    def snapshot(self) -> TwinSnapshot:
        nf_states: dict[str, dict[str, Any]] = {}
        for nf_id, nf in self._nfs.items():
            nf_states[nf_id] = {
                "type": nf.nf_type.value,
                "region": nf.region.value,
                "status": nf.status.value,
                "load": nf.load,
                "kpis": {
                    name.value: {
                        "current": kset.current,
                        "smoothed": kset.smoothed,
                        "breaching": kset.breaching,
                    }
                    for name, kset in nf.kpis.items()
                },
            }
        return TwinSnapshot(
            tick=self._tick,
            topology=self._topology,
            nf_states=nf_states,
            health_pct=self._topology.health_pct,
        )

    # ------------------------------------------------------------------
    # apply_command — external mutation (SEL invoker path)
    # ------------------------------------------------------------------
    def apply_command(
        self, service_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Route a service call to the owning NF and return the result.
        Called exclusively by the SEL Invoker (invariant P2 / TP6).
        """
        # Handle twin-level read services directly
        if service_name == "twin.snapshot":
            snap = self.snapshot()
            return {
                "tick": snap.tick,
                "health_pct": snap.health_pct,
                "nf_count": len(snap.nf_states),
            }
        if service_name == "topology.get":
            region_filter = args.get("region")
            nodes = list(self._topology.nodes.values())
            if region_filter:
                nodes = [n for n in nodes if n.region.value == region_filter]
            return {
                "nodes": [
                    {"id": n.id, "type": n.nf_type.value,
                     "region": n.region.value, "status": n.status.value}
                    for n in nodes
                ],
                "link_count": self._topology.link_count,
            }

        nf_id = args.get("target") or self._infer_owner(service_name)
        if nf_id not in self._nfs:
            raise ValueError(
                f"apply_command: no NF with id '{nf_id}' for service '{service_name}'"
            )
        return self._nfs[nf_id].handle(service_name, args)

    # ------------------------------------------------------------------
    # query helpers
    # ------------------------------------------------------------------
    def get_nf(self, nf_id: str) -> NetworkFunction | None:
        return self._nfs.get(nf_id)

    def nfs_by_type(self, nf_type: NFType) -> list[NetworkFunction]:
        return [n for n in self._nfs.values() if n.nf_type == nf_type]

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def topology(self) -> Topology:
        return self._topology

    @property
    def nf_count(self) -> int:
        return len(self._nfs)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _register(self, nf: NetworkFunction) -> None:
        self._nfs[nf.id] = nf

    def _infer_owner(self, service_name: str) -> str:
        """
        Infer the target NF id from the service prefix.
        Uses a lowercase prefix → NFType value map so casing mismatches
        don't cause failures (e.g. 'pcf' → 'PCF', 'gnb' → 'gNB').
        """
        prefix_to_nf: dict[str, str] = {
            "nrf": "NRF", "amf": "AMF", "smf": "SMF", "upf": "UPF",
            "udm": "UDM", "pcf": "PCF", "nwdaf": "NWDAF", "nef": "NEF",
            "dcf": "DCF", "af": "AF", "gnb": "gNB", "edge": "Edge",
        }
        prefix = service_name.split(".")[0].lower()
        nf_type_value = prefix_to_nf.get(prefix)

        if nf_type_value is None:
            if service_name.startswith("aimle."):
                nf_type_value = "NWDAF"
            else:
                raise ValueError(
                    f"Cannot infer owner for service '{service_name}'"
                ) from None

        candidates = [
            nf for nf in self._nfs.values()
            if nf.nf_type.value == nf_type_value and nf.is_healthy()
        ]
        if not candidates:
            raise ValueError(
                f"No healthy {nf_type_value} available for service '{service_name}'"
            )
        return sorted(c.id for c in candidates)[0]

    def _build_topology(self) -> Topology:
        """Build the initial topology from the registered NF set."""
        topo = Topology()

        # Add all NFs as nodes (excluding UEs — too many for the canvas)
        for nf in self._nfs.values():
            if nf.nf_type == NFType.UE:
                continue
            node = TopologyNode(
                id=nf.id,
                nf_type=nf.nf_type,
                region=nf.region,
                status=nf.status,
                load=nf.load,
            )
            topo = topo.add_node(node)

        # Add representative links (control-plane + user-plane)
        for region in (Region.DELHI, Region.MUMBAI):
            r = region.value.lower()
            link_specs = [
                (f"gnb_{r}_1", "amf_core_1", "N2"),
                (f"gnb_{r}_1", f"upf_{r}_1", "N3"),
                (f"gnb_{r}_2", "amf_core_1", "N2"),
                (f"gnb_{r}_2", f"upf_{r}_1", "N3"),
                (f"upf_{r}_1", f"edge_{r}_1", "N6"),
                ("smf_core_1", f"upf_{r}_1", "N4"),
                ("smf_core_1", "pcf_core_1", "N7"),
                ("amf_core_1", "udm_core_1", "N8"),
                ("nwdaf_core_1", "dcf_core_1", ""),
            ]
            for src, dst, ref in link_specs:
                if src in {n.id for n in topo.nodes.values()} \
                        and dst in {n.id for n in topo.nodes.values()}:
                    link = TopologyLink.between(src, dst, ref_point=ref)
                    # Avoid duplicate link ids
                    if link.id not in topo.links:
                        topo = topo.add_link(link)

        return topo

    def _sync_topology(self) -> None:
        """Update topology node statuses to match current NF states."""
        new_nodes = {}
        for node_id, node in self._topology.nodes.items():
            nf = self._nfs.get(node_id)
            if nf is not None:
                updated = node.with_status(nf.status, load=nf.load)
                new_nodes[node_id] = updated
            else:
                new_nodes[node_id] = node
        self._topology = Topology(nodes=new_nodes, links=self._topology.links)
