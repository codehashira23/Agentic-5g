"""
Domain: NWDAF — Network Data Analytics Function.

Role (07-network-core.md §6.9):
  The NWDAF is the analytics brain. It collects data (via DCF), hosts
  AI/ML models, and exposes analytics predictions via subscribe/notify
  and request/response.  Deploying a congestion-detection model improves
  prediction accuracy (Scenario A).

Simulated state:
  - subscriptions  : dict[sub_id → {type, region, threshold}]
  - model_instances: dict[model_id → state str]
  - analytics_accuracy : float  (KPI — improves when a model is deployed)

Produced services:
  nwdaf.analytics.congestion.subscribe / .query / .unsubscribe
  nwdaf.analytics.qos.predict
  nwdaf.analytics.load.query
  nwdaf.analytics.abnormal.subscribe
  aimle.model.deploy / .retire / .status   (model lifecycle on NWDAF target)

Standards mapping:
  spec_ref              : TS 23.288
  approximates_operation: Nnwdaf_AnalyticsInfo_Request,
                          Nnwdaf_AnalyticsSubscription_Subscribe/Notify,
                          Nnwdaf_MLModelProvision_Subscribe
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
    "nwdaf.analytics.congestion.subscribe",
    "nwdaf.analytics.congestion.query",
    "nwdaf.analytics.congestion.unsubscribe",
    "nwdaf.analytics.qos.predict",
    "nwdaf.analytics.load.query",
    "nwdaf.analytics.abnormal.subscribe",
    "nwdaf.analytics.unsubscribe",
    "aimle.model.deploy",
    "aimle.model.retire",
    "aimle.model.status",
)
_HAZARD_PROB: float = 0.001
_RECOVERY_PROB: float = 0.05
# Accuracy boost when a model is deployed
_MODEL_ACCURACY_BOOST: float = 0.15
_BASE_ACCURACY: float = 0.70


class NWDAF(NetworkFunction):
    """Simulated Network Data Analytics Function."""

    def __init__(
        self,
        nf_id: str = "nwdaf_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
    ) -> None:
        super().__init__(
            nf_id=nf_id,
            nf_type=NFType.NWDAF,
            region=region,
            services=_SERVICES,
            status=status,
        )
        self._subscriptions: dict[str, dict[str, Any]] = {}
        # model_id → {"state": "deployed"|"retired", "target": nf_id, "name": str}
        self._model_instances: dict[str, dict[str, str]] = {}
        self._set_kpi(KpiSet(
            name=KpiName.ANALYTICS_ACCURACY,
            floor=0.0, ceil=1.0,
        ))

    # ------------------------------------------------------------------
    # advance
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        events: list[DomainEvent] = []

        if self._profile.status == NFStatus.ACTIVE:
            if rng.random() < _HAZARD_PROB:
                self._set_status(NFStatus.FAILED)
                events.append(NfFailedEvent(
                    entity_id=self.id, nf_type=NFType.NWDAF.value,
                    cause="hazard", tick=ctx.tick,
                ))
                return events

            # Accuracy improves with deployed models
            deployed = sum(
                1 for m in self._model_instances.values()
                if m.get("state") == "deployed"
            )
            target_acc = min(
                1.0,
                _BASE_ACCURACY + deployed * _MODEL_ACCURACY_BOOST,
            )
            noisy_acc = target_acc + rng.gauss(0.0, 0.02)
            new_kpi = self._get_kpi(KpiName.ANALYTICS_ACCURACY).update(noisy_acc)
            self._set_kpi(new_kpi)

            events.append(KpiUpdatedEvent(
                entity_id=self.id,
                kpi=KpiName.ANALYTICS_ACCURACY.value,
                value=new_kpi.current,
                tick=ctx.tick,
            ))

        elif self._profile.status == NFStatus.FAILED:
            if rng.random() < _RECOVERY_PROB:
                self._set_status(NFStatus.ACTIVE)
                events.append(NfRecoveredEvent(
                    entity_id=self.id, nf_type=NFType.NWDAF.value, tick=ctx.tick,
                ))

        return events

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "nwdaf.analytics.congestion.subscribe":
                return self._subscribe(args, analytics_type="congestion")
            case "nwdaf.analytics.abnormal.subscribe":
                return self._subscribe(args, analytics_type="abnormal")
            case "nwdaf.analytics.congestion.query":
                return self._query_congestion(args)
            case "nwdaf.analytics.congestion.unsubscribe" | \
                 "nwdaf.analytics.unsubscribe":
                return self._unsubscribe(args)
            case "nwdaf.analytics.qos.predict":
                return self._predict_qos(args)
            case "nwdaf.analytics.load.query":
                return self._query_load(args)
            case "aimle.model.deploy":
                return self._model_deploy(args)
            case "aimle.model.retire":
                return self._model_retire(args)
            case "aimle.model.status":
                return self._model_status(args)
            case _:
                raise self._unsupported(service_name)

    # --- analytics ---
    def _subscribe(
        self, args: dict[str, Any], analytics_type: str
    ) -> dict[str, Any]:
        sub_id = f"sub_{uuid4().hex[:8]}"
        self._subscriptions[sub_id] = {
            "type": analytics_type,
            "region": args.get("region", "all"),
            "threshold": args.get("threshold"),
        }
        return {"subscription_id": sub_id, "type": analytics_type}

    def _unsubscribe(self, args: dict[str, Any]) -> dict[str, Any]:
        sub_id: str = args["subscription_id"]
        existed = sub_id in self._subscriptions
        self._subscriptions.pop(sub_id, None)
        return {"unsubscribed": existed, "subscription_id": sub_id}

    def _query_congestion(self, args: dict[str, Any]) -> dict[str, Any]:
        region: str = args.get("region", "all")
        accuracy = self._get_kpi(KpiName.ANALYTICS_ACCURACY).current
        return {
            "region": region,
            "congestion_likelihood": round(0.3 + (1.0 - accuracy) * 0.5, 3),
            "analytics_accuracy": round(accuracy, 3),
        }

    def _predict_qos(self, args: dict[str, Any]) -> dict[str, Any]:
        accuracy = self._get_kpi(KpiName.ANALYTICS_ACCURACY).current
        return {
            "region": args.get("region", "all"),
            "horizon_ticks": args.get("horizon", 10),
            "predicted_degradation": round((1.0 - accuracy) * 0.4, 3),
        }

    def _query_load(self, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "entity": args.get("nf_id", args.get("region", "all")),
            "load_estimate": round(self.load, 3),
        }

    # --- AIMLE model lifecycle ---
    def _model_deploy(self, args: dict[str, Any]) -> dict[str, Any]:
        model_id: str = args["model_id"]
        target: str = args.get("target", self.id)
        name: str = args.get("name", model_id)
        self._model_instances[model_id] = {
            "state": "deployed",
            "target": target,
            "name": name,
        }
        return {
            "model_id": model_id,
            "state": "deployed",
            "target": target,
        }

    def _model_retire(self, args: dict[str, Any]) -> dict[str, Any]:
        model_id: str = args["model_id"]
        if model_id not in self._model_instances:
            return {"retired": False, "reason": "not found"}
        self._model_instances[model_id]["state"] = "retired"
        return {"retired": True, "model_id": model_id}

    def _model_status(self, args: dict[str, Any]) -> dict[str, Any]:
        model_id: str = args["model_id"]
        if model_id not in self._model_instances:
            return {"found": False, "model_id": model_id}
        m = self._model_instances[model_id]
        return {"found": True, "model_id": model_id, **m}

    # ------------------------------------------------------------------
    # Read-only
    # ------------------------------------------------------------------
    @property
    def subscription_count(self) -> int:
        return len(self._subscriptions)

    @property
    def deployed_model_count(self) -> int:
        return sum(
            1 for m in self._model_instances.values()
            if m.get("state") == "deployed"
        )

    def has_subscription(self, sub_id: str) -> bool:
        return sub_id in self._subscriptions
