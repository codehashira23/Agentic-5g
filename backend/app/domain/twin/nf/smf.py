"""
Domain: SMF — Session Management Function.

Role (07-network-core.md §6.4):
  The SMF establishes, modifies, and releases PDU sessions.
  It selects the UPF, applies PCF policy, and tracks active sessions.

Simulated state:
  - sessions : dict[session_id → {ue_id, upf_id, qos_class}]
  - session_setup_rate : float  (KPI)

Produced services:
  smf.session.create  — establish a PDU session
  smf.session.modify  — change QoS on an existing session
  smf.session.release — tear down a session
  smf.session.list    — list sessions for a UE

Standards mapping:
  spec_ref              : TS 23.501 §6.2.2, TS 23.502 §4.3
  approximates_operation: Nsmf_PDUSession_CreateSMContext/UpdateSMContext/
                          ReleaseSMContext
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
)
from app.domain.twin.kpi import KpiName, KpiSet
from app.domain.twin.profile import NFStatus, NFType, Region

_SERVICES: tuple[str, ...] = (
    "smf.session.create",
    "smf.session.modify",
    "smf.session.release",
    "smf.session.list",
)
_HAZARD_PROB: float = 0.002
_RECOVERY_PROB: float = 0.08


class SMF(NetworkFunction):
    """Simulated Session Management Function."""

    def __init__(
        self,
        nf_id: str = "smf_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id,
            nf_type=NFType.SMF,
            region=region,
            services=_SERVICES,
            status=status,
        )
        # sessions: session_id → {ue_id, upf_id, qos_class}
        self._sessions: dict[str, dict[str, str]] = {}
        self._set_kpi(KpiSet(name=KpiName.SESSION_SETUP_RATE))

    # ------------------------------------------------------------------
    # advance
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []

        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD_PROB:
                self._set_status(NFStatus.FAILED)
                events.append(NfFailedEvent(
                    entity_id=self.id, nf_type=NFType.SMF.value,
                    cause="hazard", tick=ctx.tick,
                ))
                return events

            # Simulate session setup rate (demand-driven, with noise)
            rate = 5.0 * ctx.demand_factor + rng.gauss(0.0, 0.5)
            rate = max(0.0, rate)
            new_kpi = self._get_kpi(KpiName.SESSION_SETUP_RATE).update(rate)
            self._set_kpi(new_kpi)
            self._set_load(min(1.0, len(self._sessions) / 1000.0))

            events.append(KpiUpdatedEvent(
                entity_id=self.id, kpi=KpiName.SESSION_SETUP_RATE.value,
                value=new_kpi.current, tick=ctx.tick,
            ))

        elif self._profile.status == NFStatus.FAILED:
            if rng.random() < _RECOVERY_PROB:
                self._set_status(NFStatus.ACTIVE)
                events.append(NfRecoveredEvent(
                    entity_id=self.id, nf_type=NFType.SMF.value, tick=ctx.tick,
                ))

        return events

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "smf.session.create":
                return self._handle_create(args)
            case "smf.session.modify":
                return self._handle_modify(args)
            case "smf.session.release":
                return self._handle_release(args)
            case "smf.session.list":
                return self._handle_list(args)
            case _:
                raise self._unsupported(service_name)

    def _handle_create(self, args: dict[str, Any]) -> dict[str, Any]:
        ue_id: str = args["ue_id"]
        upf_id: str = args.get("upf_id", "upf_core_1")
        qos_class: str = args.get("qos_class", "best_effort")
        session_id = f"sess_{uuid4().hex[:8]}"
        self._sessions[session_id] = {
            "ue_id": ue_id,
            "upf_id": upf_id,
            "qos_class": qos_class,
        }
        return {
            "session_id": session_id,
            "ue_id": ue_id,
            "upf_id": upf_id,
            "qos_class": qos_class,
            "smf_id": self.id,
        }

    def _handle_modify(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id: str = args["session_id"]
        if session_id not in self._sessions:
            return {"modified": False, "reason": "session not found"}
        if "qos_class" in args:
            self._sessions[session_id]["qos_class"] = args["qos_class"]
        return {"modified": True, "session_id": session_id}

    def _handle_release(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id: str = args["session_id"]
        existed = session_id in self._sessions
        self._sessions.pop(session_id, None)
        return {"released": existed, "session_id": session_id}

    def _handle_list(self, args: dict[str, Any]) -> dict[str, Any]:
        ue_id: str | None = args.get("ue_id")
        if ue_id:
            results = {
                k: v for k, v in self._sessions.items() if v["ue_id"] == ue_id
            }
        else:
            results = dict(self._sessions)
        return {"sessions": results, "count": len(results)}

    # ------------------------------------------------------------------
    # Read-only
    # ------------------------------------------------------------------
    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def sessions(self) -> dict[str, dict[str, str]]:
        return dict(self._sessions)
