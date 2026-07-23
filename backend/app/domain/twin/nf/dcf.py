"""
Domain: DCF — Data Collection Coordination Function.

Role (07-network-core.md §6.11):
  DCF coordinates and deduplicates telemetry collection.  Consumers
  (NWDAF, agents) subscribe once; DCF fans data out without hammering
  producers.  It also maintains an ADRF-like historical repo pointer.

Produced services:
  dcf.data.subscribe / .unsubscribe / .query / .history

Standards mapping:
  spec_ref              : TS 23.288 DCCF/ADRF/MFAF
  approximates_operation: Ndccf_DataManagement_Subscribe,
                          Nadrf_DataManagement_Retrieve
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.domain.twin.entities import AdvanceContext, NetworkFunction, RngStream
from app.domain.twin.events import (
    DataCollectedEvent,
    DomainEvent,
    KpiUpdatedEvent,
    NfFailedEvent,
    NfRecoveredEvent,
)
from app.domain.twin.kpi import KpiName, KpiSet
from app.domain.twin.profile import NFStatus, NFType, Region

_SERVICES: tuple[str, ...] = (
    "dcf.data.subscribe",
    "dcf.data.unsubscribe",
    "dcf.data.query",
    "dcf.data.history",
)
_HAZARD_PROB: float = 0.001
_RECOVERY_PROB: float = 0.05


class DCF(NetworkFunction):
    """Simulated Data Collection Coordination Function."""

    def __init__(
        self,
        nf_id: str = "dcf_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id,
            nf_type=NFType.DCF,
            region=region,
            services=_SERVICES,
            status=status,
        )
        # sub_id → {producers, metrics, period}
        self._subscriptions: dict[str, dict[str, Any]] = {}
        # Simple in-memory sample store: metric → list[float]
        self._history: dict[str, list[float]] = {}
        self._set_kpi(KpiSet(name=KpiName.THROUGHPUT_MBPS))

    # ------------------------------------------------------------------
    # advance
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []

        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD_PROB:
                self._set_status(NFStatus.FAILED)
                events.append(NfFailedEvent(
                    entity_id=self.id, nf_type=NFType.DCF.value,
                    cause="hazard", tick=ctx.tick,
                ))
                return events

            # Simulate a collection cycle for each subscription
            sample_count = 0
            for sub_id, sub in self._subscriptions.items():
                producers: list[str] = sub.get("producers", [])
                metrics: list[str] = sub.get("metrics", [])
                for metric in metrics:
                    value = 10.0 * ctx.demand_factor + rng.gauss(0.0, 1.0)
                    value = max(0.0, value)
                    if metric not in self._history:
                        self._history[metric] = []
                    self._history[metric].append(value)
                    # Keep last 1000 samples to bound memory
                    if len(self._history[metric]) > 1000:
                        self._history[metric] = self._history[metric][-1000:]
                    sample_count += 1

                if sample_count > 0:
                    events.append(DataCollectedEvent(
                        subscription_id=sub_id,
                        producer_ids=tuple(producers),
                        sample_count=sample_count,
                        tick=ctx.tick,
                    ))

            # KPI: throughput proportional to subscription activity
            tp = sample_count * 0.5 + rng.gauss(0.0, 0.2)
            tp = max(0.0, tp)
            new_kpi = self._get_kpi(KpiName.THROUGHPUT_MBPS).update(tp)
            self._set_kpi(new_kpi)
            events.append(KpiUpdatedEvent(
                entity_id=self.id, kpi=KpiName.THROUGHPUT_MBPS.value,
                value=new_kpi.current, tick=ctx.tick,
            ))

        elif self._profile.status == NFStatus.FAILED:
            if rng.random() < _RECOVERY_PROB:
                self._set_status(NFStatus.ACTIVE)
                events.append(NfRecoveredEvent(
                    entity_id=self.id, nf_type=NFType.DCF.value, tick=ctx.tick,
                ))

        return events

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "dcf.data.subscribe":
                return self._handle_subscribe(args)
            case "dcf.data.unsubscribe":
                return self._handle_unsubscribe(args)
            case "dcf.data.query":
                return self._handle_query(args)
            case "dcf.data.history":
                return self._handle_history(args)
            case _:
                raise self._unsupported(service_name)

    def _handle_subscribe(self, args: dict[str, Any]) -> dict[str, Any]:
        sub_id = f"sub_{uuid4().hex[:8]}"
        self._subscriptions[sub_id] = {
            "producers": args.get("producers", []),
            "metrics": args.get("metrics", []),
            "period": args.get("period", 1),
        }
        return {"subscription_id": sub_id}

    def _handle_unsubscribe(self, args: dict[str, Any]) -> dict[str, Any]:
        sub_id: str = args["subscription_id"]
        existed = sub_id in self._subscriptions
        self._subscriptions.pop(sub_id, None)
        return {"unsubscribed": existed}

    def _handle_query(self, args: dict[str, Any]) -> dict[str, Any]:
        metric: str = args.get("metric", "")
        samples = self._history.get(metric, [])
        latest = samples[-1] if samples else 0.0
        return {"metric": metric, "value": latest, "sample_count": len(samples)}

    def _handle_history(self, args: dict[str, Any]) -> dict[str, Any]:
        metric: str = args.get("metric", args.get("kpi", ""))
        samples = self._history.get(metric, [])
        limit: int = int(args.get("limit", 100))
        return {
            "metric": metric,
            "samples": samples[-limit:],
            "total": len(samples),
        }

    @property
    def subscription_count(self) -> int:
        return len(self._subscriptions)
