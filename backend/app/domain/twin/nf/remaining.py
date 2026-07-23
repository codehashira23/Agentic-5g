"""
Domain: Remaining NF entities — PCF, UDM, NEF, AF, GNB, UE.

All follow the same pattern as AMF/SMF/UPF/NRF/NWDAF/DCF/Edge:
  - inherit NetworkFunction
  - implement advance(rng, ctx) → list[DomainEvent]
  - implement handle(service_name, args) → dict

They are grouped here to keep C046 to a manageable number of files.
Each will be split into its own module if it grows significantly.

Standards mapping per NF is documented inline.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.domain.twin.entities import AdvanceContext, NetworkFunction, RngStream
from app.domain.twin.events import (
    DomainEvent,
    KpiUpdatedEvent,
    NfFailedEvent,
    NfRecoveredEvent,
    UeAttachedEvent,
    UeHandoverEvent,
)
from app.domain.twin.kpi import KpiName, KpiSet
from app.domain.twin.profile import NFStatus, NFType, Region

_HAZARD = 0.002
_RECOVER = 0.07


def _fail_event(nf: NetworkFunction, tick: int) -> NfFailedEvent:
    return NfFailedEvent(entity_id=nf.id, nf_type=nf.nf_type.value,
                         cause="hazard", tick=tick)


def _recover_event(nf: NetworkFunction, tick: int) -> NfRecoveredEvent:
    return NfRecoveredEvent(entity_id=nf.id, nf_type=nf.nf_type.value, tick=tick)


# ===========================================================================
# PCF — Policy Control Function
# spec_ref: TS 23.501 §6.2.4, TS 23.503
# approximates_operation: Npcf_SMPolicyControl, Npcf_PolicyAuthorization
# ===========================================================================
_PCF_SERVICES: tuple[str, ...] = (
    "pcf.policy.get",
    "pcf.policy.apply",
    "pcf.policy.list",
)


class PCF(NetworkFunction):
    """Simulated Policy Control Function."""

    def __init__(
        self,
        nf_id: str = "pcf_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id, nf_type=NFType.PCF,
            region=region, services=_PCF_SERVICES, status=status,
        )
        # policy_id → {scope, qos_rule, enabled}
        self._policies: dict[str, dict[str, Any]] = {}

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD:
                self._set_status(NFStatus.FAILED)
                events.append(_fail_event(self, ctx.tick))
                return events
        elif rng.random() < _RECOVER:
            self._set_status(NFStatus.ACTIVE)
            events.append(_recover_event(self, ctx.tick))
        return events

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "pcf.policy.get":
                scope = args.get("scope", "all")
                result = {k: v for k, v in self._policies.items()
                          if scope == "all" or v.get("scope") == scope}
                return {"policies": result}
            case "pcf.policy.apply":
                pid = f"pol_{uuid4().hex[:6]}"
                self._policies[pid] = {
                    "scope": args.get("scope", "all"),
                    "qos_rule": args.get("qos_rule", "default"),
                    "enabled": True,
                }
                return {"policy_id": pid, "applied": True}
            case "pcf.policy.list":
                return {"policies": list(self._policies.keys()),
                        "count": len(self._policies)}
            case _:
                raise self._unsupported(service_name)

    @property
    def policy_count(self) -> int:
        return len(self._policies)


# ===========================================================================
# UDM — Unified Data Management
# spec_ref: TS 23.501 §6.2.7
# approximates_operation: Nudm_SDM_Get, Nudm_UECM
# NOTE: uses only SYNTHETIC subscriber data (DP8 / 07-network-core.md ND-5)
# ===========================================================================
_UDM_SERVICES: tuple[str, ...] = (
    "udm.subscriber.get",
    "udm.subscription.get",
)

# Synthetic subscriber records — no real PII (DP8)
_SYNTHETIC_SUBSCRIBERS: dict[str, dict[str, str]] = {
    f"ue_{i:04d}": {"profile": f"basic_{i % 3}", "qos_class": "standard"}
    for i in range(1, 201)  # 200 synthetic subscribers
}


class UDM(NetworkFunction):
    """
    Simulated Unified Data Management.
    All subscriber data is SYNTHETIC — no real PII (DP8).
    """

    def __init__(
        self,
        nf_id: str = "udm_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id, nf_type=NFType.UDM,
            region=region, services=_UDM_SERVICES, status=status,
        )
        self._set_kpi(KpiSet(name=KpiName.DISCOVERY_RATE))

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD:
                self._set_status(NFStatus.FAILED)
                events.append(_fail_event(self, ctx.tick))
                return events
            # Query load KPI
            rate = 20.0 * ctx.demand_factor + rng.gauss(0.0, 1.0)
            new_kpi = self._get_kpi(KpiName.DISCOVERY_RATE).update(max(0.0, rate))
            self._set_kpi(new_kpi)
            events.append(KpiUpdatedEvent(
                entity_id=self.id, kpi=KpiName.DISCOVERY_RATE.value,
                value=new_kpi.current, tick=ctx.tick,
            ))
        elif rng.random() < _RECOVER:
            self._set_status(NFStatus.ACTIVE)
            events.append(_recover_event(self, ctx.tick))
        return events

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "udm.subscriber.get":
                ue_id = args.get("ue_id", "")
                data = _SYNTHETIC_SUBSCRIBERS.get(ue_id)
                if data:
                    return {"found": True, "ue_id": ue_id, **data}
                return {"found": False, "ue_id": ue_id}
            case "udm.subscription.get":
                ue_id = args.get("ue_id", "")
                return {
                    "ue_id": ue_id,
                    "allowed_services": ["internet", "ims"],
                    "max_data_rate_mbps": 100,
                }
            case _:
                raise self._unsupported(service_name)

    @property
    def subscriber_count(self) -> int:
        return len(_SYNTHETIC_SUBSCRIBERS)


# ===========================================================================
# NEF — Network Exposure Function
# spec_ref: TS 23.501 §6.2.5; CAMARA analog
# approximates_operation: Nnef_EventExposure, Nnef_AFsessionWithQoS
# ===========================================================================
_NEF_SERVICES: tuple[str, ...] = (
    "nef.qos.request",
    "nef.event.subscribe",
    "nef.analytics.expose",
)


class NEF(NetworkFunction):
    """Simulated Network Exposure Function."""

    def __init__(
        self,
        nf_id: str = "nef_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id, nf_type=NFType.NEF,
            region=region, services=_NEF_SERVICES, status=status,
        )
        self._qos_requests: dict[str, dict[str, Any]] = {}
        self._subscriptions: dict[str, dict[str, Any]] = {}

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD:
                self._set_status(NFStatus.FAILED)
                events.append(_fail_event(self, ctx.tick))
        elif rng.random() < _RECOVER:
            self._set_status(NFStatus.ACTIVE)
            events.append(_recover_event(self, ctx.tick))
        return events

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "nef.qos.request":
                req_id = f"qos_{uuid4().hex[:6]}"
                self._qos_requests[req_id] = args
                return {"request_id": req_id, "status": "accepted"}
            case "nef.event.subscribe":
                sub_id = f"sub_{uuid4().hex[:6]}"
                self._subscriptions[sub_id] = args
                return {"subscription_id": sub_id}
            case "nef.analytics.expose":
                return {
                    "analytics_type": args.get("analytics_type", "generic"),
                    "scope": args.get("scope", "all"),
                    "available": True,
                }
            case _:
                raise self._unsupported(service_name)


# ===========================================================================
# AF — Application Function
# spec_ref: TS 23.501 AF concepts, TS 23.502 §4.15
# approximates_operation: AF influence via Nnef_* / Npcf_PolicyAuthorization
# ===========================================================================
_AF_SERVICES: tuple[str, ...] = (
    "af.session.report",
    "af.demand.raise",
)


class AF(NetworkFunction):
    """Simulated Application Function (external app consumer)."""

    def __init__(
        self,
        nf_id: str = "af_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id, nf_type=NFType.AF,
            region=region, services=_AF_SERVICES, status=status,
        )
        self._app_sessions: list[str] = []

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD:
                self._set_status(NFStatus.FAILED)
                events.append(_fail_event(self, ctx.tick))
        elif rng.random() < _RECOVER:
            self._set_status(NFStatus.ACTIVE)
            events.append(_recover_event(self, ctx.tick))
        return events

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "af.session.report":
                return {"reported": True, "session_count": len(self._app_sessions)}
            case "af.demand.raise":
                return {"demand_raised": True,
                        "qos_target": args.get("qos_target", "default")}
            case _:
                raise self._unsupported(service_name)


# ===========================================================================
# GNB — Radio Base Station
# spec_ref: TS 38-series (RAN) at role level; N2/N3 (TS 23.501)
# Models radio statistically; no real RRC/NGAP
# ===========================================================================
_GNB_SERVICES: tuple[str, ...] = ("gnb.metrics.get",)


class GNB(NetworkFunction):
    """Simulated 5G base station (gNodeB)."""

    def __init__(
        self,
        nf_id: str = "gnb_delhi_1",
        region: Region = Region.DELHI,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id, nf_type=NFType.GNB,
            region=region, services=_GNB_SERVICES, status=status,
        )
        self._connected_ue_ids: set[str] = set()
        self._set_kpi(KpiSet.for_utilization(
            KpiName.PRB_UTILIZATION, high=0.85, low=0.70
        ))

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD:
                self._set_status(NFStatus.FAILED)
                events.append(_fail_event(self, ctx.tick))
                return events

            # PRB utilisation driven by connected UEs + demand
            ue_load = len(self._connected_ue_ids) / max(1, 100)
            prb = min(0.99, ue_load * ctx.demand_factor + rng.gauss(0.0, 0.02))
            prb = max(0.0, prb)
            new_kpi = self._get_kpi(KpiName.PRB_UTILIZATION).update(prb)
            self._set_kpi(new_kpi)
            self._set_load(prb)
            events.append(KpiUpdatedEvent(
                entity_id=self.id, kpi=KpiName.PRB_UTILIZATION.value,
                value=new_kpi.current, tick=ctx.tick,
            ))

            # Occasional UE handover (mobility)
            if self._connected_ue_ids and rng.random() < 0.02:
                ue_id = next(iter(self._connected_ue_ids))
                events.append(UeHandoverEvent(
                    ue_id=ue_id,
                    from_gnb=self.id,
                    to_gnb=f"gnb_{self.region.value.lower()}_2",
                    region=self.region.value,
                    tick=ctx.tick,
                ))
        elif rng.random() < _RECOVER:
            self._set_status(NFStatus.ACTIVE)
            events.append(_recover_event(self, ctx.tick))
        return events

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if service_name == "gnb.metrics.get":
            return {
                "prb_utilization": self._get_kpi(KpiName.PRB_UTILIZATION).current,
                "connected_ue_count": len(self._connected_ue_ids),
            }
        raise self._unsupported(service_name)

    def attach_ue(self, ue_id: str) -> None:
        self._connected_ue_ids.add(ue_id)

    def detach_ue(self, ue_id: str) -> None:
        self._connected_ue_ids.discard(ue_id)

    @property
    def ue_count(self) -> int:
        return len(self._connected_ue_ids)


# ===========================================================================
# UE — User Equipment
# spec_ref: TS 23.501 UE concepts
# Not a service producer; models demand + mobility
# ===========================================================================
class UE(NetworkFunction):
    """
    Simulated User Equipment (end device).
    Not a service producer in SBA — it is a demand + mobility source.
    """

    def __init__(
        self,
        nf_id: str = "ue_0001",
        region: Region = Region.DELHI,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id, nf_type=NFType.UE,
            region=region, services=(), status=status,
        )
        self._attached_gnb: str | None = None
        self._sessions: list[str] = []
        self._traffic_demand_mbps: float = 1.0

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self._profile.status == NFStatus.ACTIVE:
            # Traffic demand fluctuates with diurnal demand_factor
            self._traffic_demand_mbps = max(
                0.1,
                1.0 * ctx.demand_factor + rng.gauss(0.0, 0.2),
            )

            # Occasional mobility — move to another gNB in the region
            if self._attached_gnb and rng.random() < 0.01:
                new_gnb = f"gnb_{self.region.value.lower()}_2"
                events.append(UeHandoverEvent(
                    ue_id=self.id,
                    from_gnb=self._attached_gnb,
                    to_gnb=new_gnb,
                    region=self.region.value,
                    tick=ctx.tick,
                ))
                self._attached_gnb = new_gnb

            # Attach if not connected yet
            if not self._attached_gnb:
                gnb_id = f"gnb_{self.region.value.lower()}_1"
                self._attached_gnb = gnb_id
                events.append(UeAttachedEvent(
                    ue_id=self.id,
                    gnb_id=gnb_id,
                    region=self.region.value,
                    tick=ctx.tick,
                ))
        return events

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        # UE is not a service producer in SBA
        raise self._unsupported(service_name)

    @property
    def traffic_demand_mbps(self) -> float:
        return self._traffic_demand_mbps

    @property
    def attached_gnb(self) -> str | None:
        return self._attached_gnb
