"""
Domain: UPF — User Plane Function.

Role (07-network-core.md §6.5):
  The UPF does the actual packet forwarding.  It is the primary
  determinant of user-experienced latency, throughput, and packet loss.
  Load on the UPF drives the latency KPI via an M/M/1-style curve.

Simulated state:
  - served_sessions : set[str]      — session ids currently anchored here
  - throughput_mbps : float         (KPI)
  - latency_ms      : float         (KPI — the main agent-visible signal)
  - packet_loss     : float         (KPI)

Produced services:
  upf.session.install   — anchor a session on this UPF
  upf.session.remove    — release a session
  upf.loadbalance.apply — shift a fraction of sessions (agent action)
  upf.metrics.get       — return current KPIs

Standards mapping:
  spec_ref              : TS 23.501 §6.2.3; N4 (TS 29.244 PFCP at role level)
  approximates_operation: N4 session management + user-plane forwarding

Latency model (06-digital-twin.md §10):
  base_latency + load_factor * (1 / (1 - utilisation))  clamped to [1, 200] ms
  This is an M/M/1-style queuing approximation.
"""
from __future__ import annotations

from typing import Any

from app.domain.twin.entities import AdvanceContext, NetworkFunction, RngStream
from app.domain.twin.events import (
    DomainEvent,
    KpiUpdatedEvent,
    NfFailedEvent,
    NfRecoveredEvent,
)
from app.domain.twin.kpi import KpiName, KpiSet
from app.domain.twin.profile import NFStatus, NFType, Region

_SERVICES: tuple[str, ...] = (
    "upf.session.install",
    "upf.session.remove",
    "upf.loadbalance.apply",
    "upf.metrics.get",
)
_HAZARD_PROB: float = 0.003
_RECOVERY_PROB: float = 0.06

# Latency model constants
_BASE_LATENCY_MS: float = 5.0     # minimum latency at zero load
_LOAD_FACTOR: float = 8.0         # how steeply latency rises with load
_MAX_SESSIONS: int = 500          # normalisation denominator for utilisation


class UPF(NetworkFunction):
    """Simulated User Plane Function."""

    def __init__(
        self,
        nf_id: str = "upf_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
        base_latency_ms: float = _BASE_LATENCY_MS,
    ) -> None:
        super().__init__(
            nf_id=nf_id,
            nf_type=NFType.UPF,
            region=region,
            services=_SERVICES,
            status=status,
        )
        self._served_sessions: set[str] = set()
        self._base_latency_ms: float = base_latency_ms  # Edge UPFs have lower base

        # Initialise KPIs with thresholds from 04-ui.md / demo defaults
        self._set_kpi(KpiSet.for_latency(high_ms=20.0, low_ms=15.0))
        self._set_kpi(KpiSet(name=KpiName.THROUGHPUT_MBPS))
        self._set_kpi(KpiSet.for_utilization(KpiName.PACKET_LOSS,
                                             high=0.02, low=0.01))

    # ------------------------------------------------------------------
    # advance
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []

        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD_PROB:
                self._set_status(NFStatus.FAILED)
                events.append(NfFailedEvent(
                    entity_id=self.id, nf_type=NFType.UPF.value,
                    cause="hazard", tick=ctx.tick,
                ))
                return events

            # --- Utilisation ---
            utilisation = min(
                0.99,
                len(self._served_sessions) / _MAX_SESSIONS * ctx.demand_factor,
            )
            self._set_load(utilisation)

            # --- Latency (M/M/1-style): base / (1 - u) + noise ---
            if utilisation < 0.99:
                raw_latency = (
                    self._base_latency_ms / (1.0 - utilisation)
                    + rng.gauss(0.0, 1.0)
                )
            else:
                raw_latency = 200.0   # saturated
            new_lat = self._get_kpi(KpiName.LATENCY_MS).update(raw_latency)
            self._set_kpi(new_lat)

            # --- Throughput (demand-proportional) ---
            raw_tp = 100.0 * ctx.demand_factor * utilisation + rng.gauss(0.0, 2.0)
            raw_tp = max(0.0, raw_tp)
            new_tp = self._get_kpi(KpiName.THROUGHPUT_MBPS).update(raw_tp)
            self._set_kpi(new_tp)

            # --- Packet loss (rises steeply near saturation) ---
            raw_loss = max(0.0, (utilisation - 0.7) / 0.3 * 0.05
                          + rng.gauss(0.0, 0.002))
            raw_loss = max(0.0, raw_loss)
            new_loss = self._get_kpi(KpiName.PACKET_LOSS).update(raw_loss)
            self._set_kpi(new_loss)

            # Emit KPI events for the three main metrics
            for kpi_set in (new_lat, new_tp, new_loss):
                events.append(KpiUpdatedEvent(
                    entity_id=self.id,
                    kpi=kpi_set.name.value,
                    value=kpi_set.current,
                    tick=ctx.tick,
                ))

        elif self._profile.status == NFStatus.FAILED:
            if rng.random() < _RECOVERY_PROB:
                self._set_status(NFStatus.ACTIVE)
                events.append(NfRecoveredEvent(
                    entity_id=self.id, nf_type=NFType.UPF.value, tick=ctx.tick,
                ))

        return events

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "upf.session.install":
                return self._handle_install(args)
            case "upf.session.remove":
                return self._handle_remove(args)
            case "upf.loadbalance.apply":
                return self._handle_loadbalance(args)
            case "upf.metrics.get":
                return self._handle_metrics()
            case _:
                raise self._unsupported(service_name)

    def _handle_install(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id: str = args["session_id"]
        self._served_sessions.add(session_id)
        return {"installed": True, "session_id": session_id, "upf_id": self.id}

    def _handle_remove(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id: str = args["session_id"]
        existed = session_id in self._served_sessions
        self._served_sessions.discard(session_id)
        return {"removed": existed, "session_id": session_id}

    def _handle_loadbalance(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Shift a fraction of sessions off this UPF (agent mitigation action).
        Compensation service: restore the same count.
        """
        fraction: float = float(args.get("fraction", 0.3))
        fraction = max(0.0, min(1.0, fraction))
        count_to_move = int(len(self._served_sessions) * fraction)
        moved: list[str] = []
        sessions_copy = list(self._served_sessions)
        for sess_id in sessions_copy[:count_to_move]:
            self._served_sessions.discard(sess_id)
            moved.append(sess_id)
        return {
            "moved_count": len(moved),
            "moved_session_ids": moved,
            "remaining": len(self._served_sessions),
        }

    def _handle_metrics(self) -> dict[str, Any]:
        from app.domain.twin.kpi import KpiName as K
        return {
            "latency_ms": self._get_kpi(K.LATENCY_MS).current,
            "throughput_mbps": self._get_kpi(K.THROUGHPUT_MBPS).current,
            "packet_loss": self._get_kpi(K.PACKET_LOSS).current,
            "session_count": len(self._served_sessions),
            "load": self.load,
        }

    # ------------------------------------------------------------------
    # Read-only
    # ------------------------------------------------------------------
    @property
    def session_count(self) -> int:
        return len(self._served_sessions)

    @property
    def latency_ms(self) -> float:
        return self._get_kpi(KpiName.LATENCY_MS).current
