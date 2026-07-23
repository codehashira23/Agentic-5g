"""
Domain: Edge Node — edge compute node.

Role (07-network-core.md §6.13):
  Hosts AIMLE models close to users, reducing base_latency for
  edge-served traffic.  The primary target of Scenario A.

Simulated state:
  - hosted_models: dict[model_id → model_name]
  - base_latency_ms: lowered when models are deployed
  - compute_load: float KPI

Produced services:
  edge.model.host   — deploy a model to this edge node (AIMLE path)
  edge.model.run    — invoke inference (modelled delay)
  edge.metrics.get  — return current metrics
  aimle.model.deploy / .retire / .status  (edge-side AIMLE lifecycle)

Standards mapping:
  spec_ref              : TS 23.548 (EDGEAPP concepts)
  approximates_operation: local model hosting/inference (modelled), N6 to DN
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
    "edge.model.host",
    "edge.model.run",
    "edge.metrics.get",
    "aimle.model.deploy",
    "aimle.model.retire",
    "aimle.model.status",
)
_HAZARD_PROB: float = 0.002
_RECOVERY_PROB: float = 0.06
# Base latency drops by this amount per hosted model (ms)
_LATENCY_REDUCTION_PER_MODEL: float = 2.0
_DEFAULT_BASE_LATENCY_MS: float = 5.0


class EdgeNode(NetworkFunction):
    """Simulated edge compute node."""

    def __init__(
        self,
        nf_id: str = "edge_delhi_1",
        region: Region = Region.DELHI,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id,
            nf_type=NFType.EDGE,
            region=region,
            services=_SERVICES,
            status=status,
        )
        # model_id → {"name": str, "state": "deployed"|"retired"}
        self._hosted_models: dict[str, dict[str, str]] = {}
        self._set_kpi(KpiSet.for_utilization(
            KpiName.COMPUTE_LOAD, high=0.85, low=0.70
        ))
        self._set_kpi(KpiSet.for_latency(high_ms=15.0, low_ms=10.0))

    # ------------------------------------------------------------------
    # advance
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []

        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD_PROB:
                self._set_status(NFStatus.FAILED)
                events.append(NfFailedEvent(
                    entity_id=self.id, nf_type=NFType.EDGE.value,
                    cause="hazard", tick=ctx.tick,
                ))
                return events

            # Compute load scales with hosted models + demand
            active_models = sum(
                1 for m in self._hosted_models.values()
                if m.get("state") == "deployed"
            )
            raw_load = (
                active_models * 0.15 * ctx.demand_factor
                + rng.gauss(0.0, 0.02)
            )
            raw_load = max(0.0, min(1.0, raw_load))
            new_compute = self._get_kpi(KpiName.COMPUTE_LOAD).update(raw_load)
            self._set_kpi(new_compute)
            self._set_load(raw_load)

            # Latency drops with each deployed model (proximity benefit)
            base_ms = max(
                1.0,
                _DEFAULT_BASE_LATENCY_MS
                - active_models * _LATENCY_REDUCTION_PER_MODEL,
            )
            raw_lat = base_ms / (1.0 - raw_load * 0.5) + rng.gauss(0.0, 0.5)
            raw_lat = max(1.0, raw_lat)
            new_lat = self._get_kpi(KpiName.LATENCY_MS).update(raw_lat)
            self._set_kpi(new_lat)

            for kpi_set in (new_compute, new_lat):
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
                    entity_id=self.id, nf_type=NFType.EDGE.value, tick=ctx.tick,
                ))

        return events

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "edge.model.host" | "aimle.model.deploy":
                return self._handle_deploy(args)
            case "edge.model.run":
                return self._handle_run(args)
            case "edge.metrics.get":
                return self._handle_metrics()
            case "aimle.model.retire":
                return self._handle_retire(args)
            case "aimle.model.status":
                return self._handle_status(args)
            case _:
                raise self._unsupported(service_name)

    def _handle_deploy(self, args: dict[str, Any]) -> dict[str, Any]:
        model_id: str = args["model_id"]
        name: str = args.get("name", model_id)
        self._hosted_models[model_id] = {"name": name, "state": "deployed"}
        return {
            "model_id": model_id,
            "state": "deployed",
            "target": self.id,
            "region": self.region.value,
        }

    def _handle_run(self, args: dict[str, Any]) -> dict[str, Any]:
        model_id: str = args["model_id"]
        if model_id not in self._hosted_models:
            return {"ran": False, "reason": "model not hosted"}
        if self._hosted_models[model_id].get("state") != "deployed":
            return {"ran": False, "reason": "model not deployed"}
        return {"ran": True, "model_id": model_id, "latency_ms": self.latency_ms}

    def _handle_retire(self, args: dict[str, Any]) -> dict[str, Any]:
        model_id: str = args["model_id"]
        if model_id not in self._hosted_models:
            return {"retired": False, "reason": "not found"}
        self._hosted_models[model_id]["state"] = "retired"
        return {"retired": True, "model_id": model_id}

    def _handle_status(self, args: dict[str, Any]) -> dict[str, Any]:
        model_id: str = args["model_id"]
        if model_id not in self._hosted_models:
            return {"found": False, "model_id": model_id}
        return {"found": True, "model_id": model_id,
                **self._hosted_models[model_id]}

    def _handle_metrics(self) -> dict[str, Any]:
        return {
            "compute_load": self._get_kpi(KpiName.COMPUTE_LOAD).current,
            "latency_ms": self.latency_ms,
            "hosted_model_count": self.deployed_model_count,
        }

    # ------------------------------------------------------------------
    # Read-only
    # ------------------------------------------------------------------
    @property
    def deployed_model_count(self) -> int:
        return sum(
            1 for m in self._hosted_models.values()
            if m.get("state") == "deployed"
        )

    @property
    def latency_ms(self) -> float:
        return self._get_kpi(KpiName.LATENCY_MS).current
