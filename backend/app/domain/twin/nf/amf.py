"""
Domain: AMF — Access and Mobility Management Function.

Role (07-network-core.md §6.3):
  The AMF is the control anchor for UEs — it handles registration,
  connection, and mobility.  Every UE attaches through an AMF.

Simulated state:
  - registered_ues : set[str]   — UE ids currently attached
  - registration_load : float  — registrations per tick (KPI)

Produced services:
  amf.ue.register   — attach a UE
  amf.ue.deregister — detach a UE
  amf.ue.context.get — return a UE's context

Standards mapping:
  spec_ref              : TS 23.501 §6.2.1, TS 23.502 §4.2
  approximates_operation: Namf_Communication, Namf_EventExposure
"""
from __future__ import annotations

from typing import Any

from app.domain.twin.entities import AdvanceContext, NetworkFunction, RngStream
from app.domain.twin.events import (
    DomainEvent,
    KpiUpdatedEvent,
    NfFailedEvent,
    NfRecoveredEvent,
    UeAttachedEvent,
)
from app.domain.twin.kpi import KpiName, KpiSet
from app.domain.twin.profile import NFStatus, NFType, Region

_SERVICES: tuple[str, ...] = (
    "amf.ue.register",
    "amf.ue.deregister",
    "amf.ue.context.get",
    "amf.mobility.notify",
)
_HAZARD_PROB: float = 0.002
_RECOVERY_PROB: float = 0.08


class AMF(NetworkFunction):
    """Simulated Access and Mobility Management Function."""

    def __init__(
        self,
        nf_id: str = "amf_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id,
            nf_type=NFType.AMF,
            region=region,
            services=_SERVICES,
            status=status,
        )
        self._registered_ues: set[str] = set()
        self._set_kpi(KpiSet(name=KpiName.REGISTRATION_LOAD))

    # ------------------------------------------------------------------
    # advance
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []

        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD_PROB:
                self._set_status(NFStatus.FAILED)
                events.append(NfFailedEvent(
                    entity_id=self.id, nf_type=NFType.AMF.value,
                    cause="hazard", tick=ctx.tick,
                ))
                return events

            # Simulate UE churn — occasionally a UE attaches
            if rng.random() < 0.1 * ctx.demand_factor:
                ue_id = f"ue_{ctx.tick}_{int(rng.uniform(1000, 9999))}"
                self._registered_ues.add(ue_id)
                events.append(UeAttachedEvent(
                    ue_id=ue_id,
                    gnb_id=f"gnb_{self.region.value.lower()}_1",
                    region=self.region.value, tick=ctx.tick,
                ))

            # KPI: registration_load
            load = len(self._registered_ues) * ctx.demand_factor * 0.5
            load += rng.gauss(0.0, 0.5)
            load = max(0.0, load)
            new_kpi = self._get_kpi(KpiName.REGISTRATION_LOAD).update(load)
            self._set_kpi(new_kpi)
            self._set_load(min(1.0, load / 100.0))

            events.append(KpiUpdatedEvent(
                entity_id=self.id, kpi=KpiName.REGISTRATION_LOAD.value,
                value=new_kpi.current, tick=ctx.tick,
            ))

        elif self._profile.status == NFStatus.FAILED:
            if rng.random() < _RECOVERY_PROB:
                self._set_status(NFStatus.ACTIVE)
                events.append(NfRecoveredEvent(
                    entity_id=self.id, nf_type=NFType.AMF.value, tick=ctx.tick,
                ))

        return events

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "amf.ue.register":
                return self._handle_ue_register(args)
            case "amf.ue.deregister":
                return self._handle_ue_deregister(args)
            case "amf.ue.context.get":
                return self._handle_ue_context(args)
            case "amf.mobility.notify":
                return {"notified": True}
            case _:
                raise self._unsupported(service_name)

    def _handle_ue_register(self, args: dict[str, Any]) -> dict[str, Any]:
        ue_id: str = args["ue_id"]
        self._registered_ues.add(ue_id)
        return {"registered": True, "ue_id": ue_id, "amf_id": self.id}

    def _handle_ue_deregister(self, args: dict[str, Any]) -> dict[str, Any]:
        ue_id: str = args["ue_id"]
        existed = ue_id in self._registered_ues
        self._registered_ues.discard(ue_id)
        return {"deregistered": existed, "ue_id": ue_id}

    def _handle_ue_context(self, args: dict[str, Any]) -> dict[str, Any]:
        ue_id: str = args["ue_id"]
        if ue_id not in self._registered_ues:
            return {"found": False, "ue_id": ue_id}
        return {
            "found": True,
            "ue_id": ue_id,
            "amf_id": self.id,
            "region": self.region.value,
        }

    # ------------------------------------------------------------------
    # Read-only
    # ------------------------------------------------------------------
    @property
    def registered_ues(self) -> frozenset[str]:
        return frozenset(self._registered_ues)

    @property
    def ue_count(self) -> int:
        return len(self._registered_ues)
