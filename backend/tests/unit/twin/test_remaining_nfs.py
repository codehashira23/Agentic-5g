"""
C046: Tests for NWDAF, DCF, Edge, PCF, UDM, NEF, AF, GNB, UE.

Priority: NWDAF + Edge (Scenario A critical) get thorough tests.
PCF/UDM/NEF/AF/GNB/UE get focused smoke tests.
"""
from __future__ import annotations

import pytest
from app.domain.twin.entities import AdvanceContext
from app.domain.twin.events import (
    DataCollectedEvent,
    KpiUpdatedEvent,
    NfFailedEvent,
    NfRecoveredEvent,
    UeAttachedEvent,
)
from app.domain.twin.kpi import KpiName
from app.domain.twin.nf.dcf import DCF
from app.domain.twin.nf.edge import EdgeNode
from app.domain.twin.nf.nwdaf import NWDAF
from app.domain.twin.nf.remaining import AF, GNB, NEF, PCF, UDM, UE
from app.domain.twin.profile import NFStatus, NFType, Region


class FakeRng:
    def __init__(self, fixed: float = 0.5) -> None:
        self._fixed = fixed

    def random(self) -> float:
        return self._fixed

    def gauss(self, mu: float, sigma: float) -> float:
        return mu

    def uniform(self, lo: float, hi: float) -> float:
        return (lo + hi) / 2.0


def ctx(tick: int = 1, demand: float = 1.0) -> AdvanceContext:
    return AdvanceContext(tick=tick, demand_factor=demand)


# ===========================================================================
# NWDAF
# ===========================================================================
class TestNWDAFConstruction:
    def test_defaults(self) -> None:
        n = NWDAF()
        assert n.id == "nwdaf_core_1"
        assert n.nf_type == NFType.NWDAF
        assert n.subscription_count == 0
        assert n.deployed_model_count == 0

    def test_produces_aimle_services(self) -> None:
        n = NWDAF()
        assert "aimle.model.deploy" in n.profile.services
        assert "aimle.model.retire" in n.profile.services
        assert "aimle.model.status" in n.profile.services


class TestNWDAFSubscriptions:
    def test_subscribe_congestion(self) -> None:
        n = NWDAF()
        result = n.handle("nwdaf.analytics.congestion.subscribe",
                          {"region": "Delhi"})
        assert "subscription_id" in result
        assert n.subscription_count == 1

    def test_unsubscribe(self) -> None:
        n = NWDAF()
        sub = n.handle("nwdaf.analytics.congestion.subscribe", {"region": "Delhi"})
        n.handle("nwdaf.analytics.unsubscribe",
                 {"subscription_id": sub["subscription_id"]})
        assert n.subscription_count == 0

    def test_subscribe_returns_unique_ids(self) -> None:
        n = NWDAF()
        r1 = n.handle("nwdaf.analytics.congestion.subscribe", {"region": "Delhi"})
        r2 = n.handle("nwdaf.analytics.congestion.subscribe", {"region": "Mumbai"})
        assert r1["subscription_id"] != r2["subscription_id"]

    def test_subscription_can_be_retrieved(self) -> None:
        n = NWDAF()
        r = n.handle("nwdaf.analytics.congestion.subscribe", {"region": "Delhi"})
        assert n.has_subscription(r["subscription_id"])


class TestNWDAFModelLifecycle:
    def test_deploy_model(self) -> None:
        n = NWDAF()
        result = n.handle("aimle.model.deploy",
                          {"model_id": "congestion-det", "target": "nwdaf_core_1"})
        assert result["state"] == "deployed"
        assert n.deployed_model_count == 1

    def test_deploy_multiple_models(self) -> None:
        n = NWDAF()
        n.handle("aimle.model.deploy",
                 {"model_id": "model_a", "target": "nwdaf_core_1"})
        n.handle("aimle.model.deploy",
                 {"model_id": "model_b", "target": "nwdaf_core_1"})
        assert n.deployed_model_count == 2

    def test_retire_model(self) -> None:
        n = NWDAF()
        n.handle("aimle.model.deploy",
                 {"model_id": "m1", "target": "nwdaf_core_1"})
        result = n.handle("aimle.model.retire", {"model_id": "m1"})
        assert result["retired"] is True
        assert n.deployed_model_count == 0

    def test_model_status(self) -> None:
        n = NWDAF()
        n.handle("aimle.model.deploy",
                 {"model_id": "m1", "target": "nwdaf_core_1"})
        result = n.handle("aimle.model.status", {"model_id": "m1"})
        assert result["found"] is True
        assert result["state"] == "deployed"

    def test_model_status_not_found(self) -> None:
        n = NWDAF()
        result = n.handle("aimle.model.status", {"model_id": "none"})
        assert result["found"] is False

    def test_retire_unknown_model(self) -> None:
        n = NWDAF()
        result = n.handle("aimle.model.retire", {"model_id": "ghost"})
        assert result["retired"] is False


class TestNWDAFAccuracyImproves:
    def test_accuracy_improves_with_deployed_model(self) -> None:
        """
        Deploying a model boosts the accuracy target.
        After several ticks with a model deployed, accuracy > base.
        """
        n = NWDAF()
        n.handle("aimle.model.deploy",
                 {"model_id": "congestion-det", "target": "nwdaf_core_1"})
        for tick in range(1, 20):
            n.advance(FakeRng(0.5), ctx(tick=tick))
        accuracy = n.kpis[KpiName.ANALYTICS_ACCURACY].current
        assert accuracy > 0.70  # above base accuracy

    def test_accuracy_without_model_stays_near_base(self) -> None:
        n = NWDAF()
        for tick in range(1, 20):
            n.advance(FakeRng(0.5), ctx(tick=tick))
        accuracy = n.kpis[KpiName.ANALYTICS_ACCURACY].smoothed
        assert accuracy <= 0.75  # near base, no model boost


class TestNWDAFAdvance:
    def test_emits_kpi_updated(self) -> None:
        n = NWDAF()
        events = n.advance(FakeRng(0.5), ctx(tick=1))
        assert any(isinstance(e, KpiUpdatedEvent) for e in events)

    def test_failure_on_low_rng(self) -> None:
        n = NWDAF()
        events = n.advance(FakeRng(0.0), ctx(tick=1))
        assert any(isinstance(e, NfFailedEvent) for e in events)
        assert n.status == NFStatus.FAILED

    def test_recovery_from_failed(self) -> None:
        n = NWDAF(status=NFStatus.FAILED)
        events = n.advance(FakeRng(0.0), ctx(tick=2))
        assert any(isinstance(e, NfRecoveredEvent) for e in events)


# ===========================================================================
# DCF
# ===========================================================================
class TestDCFSubscriptions:
    def test_subscribe(self) -> None:
        d = DCF()
        result = d.handle("dcf.data.subscribe", {
            "producers": ["upf_delhi_1"],
            "metrics": ["latency_ms"],
        })
        assert "subscription_id" in result
        assert d.subscription_count == 1

    def test_unsubscribe(self) -> None:
        d = DCF()
        sub = d.handle("dcf.data.subscribe", {"producers": [], "metrics": []})
        d.handle("dcf.data.unsubscribe",
                 {"subscription_id": sub["subscription_id"]})
        assert d.subscription_count == 0

    def test_history_after_advance(self) -> None:
        d = DCF()
        d.handle("dcf.data.subscribe", {
            "producers": ["upf_1"],
            "metrics": ["latency_ms"],
        })
        for tick in range(1, 6):
            d.advance(FakeRng(0.5), ctx(tick=tick))
        result = d.handle("dcf.data.history", {"metric": "latency_ms"})
        assert result["total"] == 5

    def test_query_returns_latest(self) -> None:
        d = DCF()
        d.handle("dcf.data.subscribe", {
            "producers": ["upf_1"],
            "metrics": ["throughput_mbps"],
        })
        d.advance(FakeRng(0.5), ctx(tick=1))
        result = d.handle("dcf.data.query", {"metric": "throughput_mbps"})
        assert result["value"] >= 0.0

    def test_advance_emits_data_collected(self) -> None:
        d = DCF()
        d.handle("dcf.data.subscribe", {
            "producers": ["upf_1"],
            "metrics": ["latency_ms"],
        })
        events = d.advance(FakeRng(0.5), ctx(tick=1))
        assert any(isinstance(e, DataCollectedEvent) for e in events)


# ===========================================================================
# EdgeNode — critical for Scenario A
# ===========================================================================
class TestEdgeConstruction:
    def test_defaults(self) -> None:
        e = EdgeNode()
        assert e.id == "edge_delhi_1"
        assert e.nf_type == NFType.EDGE
        assert e.region == Region.DELHI
        assert e.deployed_model_count == 0

    def test_produces_aimle_services(self) -> None:
        e = EdgeNode()
        assert "aimle.model.deploy" in e.profile.services
        assert "aimle.model.retire" in e.profile.services
        assert "edge.model.host" in e.profile.services

    def test_latency_kpi_thresholds(self) -> None:
        e = EdgeNode()
        lat = e.kpis[KpiName.LATENCY_MS]
        assert lat.high_threshold == 15.0   # edge has lower threshold
        assert lat.low_threshold == 10.0


class TestEdgeModelDeploy:
    def test_deploy_model(self) -> None:
        e = EdgeNode()
        result = e.handle("aimle.model.deploy", {
            "model_id": "congestion-det",
            "name": "Congestion Detection v1",
        })
        assert result["state"] == "deployed"
        assert result["target"] == "edge_delhi_1"
        assert e.deployed_model_count == 1

    def test_deploy_via_edge_model_host(self) -> None:
        e = EdgeNode()
        result = e.handle("edge.model.host", {
            "model_id": "m2", "name": "Model 2",
        })
        assert result["state"] == "deployed"

    def test_retire_model(self) -> None:
        e = EdgeNode()
        e.handle("aimle.model.deploy",
                 {"model_id": "m1", "name": "M1"})
        result = e.handle("aimle.model.retire", {"model_id": "m1"})
        assert result["retired"] is True
        assert e.deployed_model_count == 0

    def test_model_status(self) -> None:
        e = EdgeNode()
        e.handle("aimle.model.deploy",
                 {"model_id": "m1", "name": "M1"})
        result = e.handle("aimle.model.status", {"model_id": "m1"})
        assert result["found"] is True
        assert result["state"] == "deployed"

    def test_run_deployed_model(self) -> None:
        e = EdgeNode()
        e.handle("aimle.model.deploy",
                 {"model_id": "m1", "name": "M1"})
        result = e.handle("edge.model.run", {"model_id": "m1"})
        assert result["ran"] is True

    def test_run_unhosted_model_fails_gracefully(self) -> None:
        e = EdgeNode()
        result = e.handle("edge.model.run", {"model_id": "ghost"})
        assert result["ran"] is False

    def test_metrics_returns_expected_keys(self) -> None:
        e = EdgeNode()
        result = e.handle("edge.metrics.get", {})
        for key in ("compute_load", "latency_ms", "hosted_model_count"):
            assert key in result


class TestEdgeLatencyReducedByModel:
    def test_latency_lower_with_model_than_without(self) -> None:
        """
        Deploying a model reduces base_latency.  After advancing,
        the edge with a model should have lower latency.
        """
        e_no_model = EdgeNode(nf_id="edge_a")
        e_with_model = EdgeNode(nf_id="edge_b")
        e_with_model.handle("aimle.model.deploy",
                            {"model_id": "m1", "name": "M1"})

        rng = FakeRng(0.5)
        for tick in range(1, 10):
            e_no_model.advance(rng, ctx(tick=tick))
            e_with_model.advance(rng, ctx(tick=tick))

        assert e_with_model.latency_ms < e_no_model.latency_ms


class TestEdgeAdvance:
    def test_emits_two_kpi_events(self) -> None:
        e = EdgeNode()
        events = e.advance(FakeRng(0.5), ctx(tick=1))
        kpi_events = [ev for ev in events if isinstance(ev, KpiUpdatedEvent)]
        assert len(kpi_events) == 2

    def test_failure_on_low_rng(self) -> None:
        e = EdgeNode()
        events = e.advance(FakeRng(0.0), ctx(tick=1))
        assert any(isinstance(ev, NfFailedEvent) for ev in events)
        assert e.status == NFStatus.FAILED

    def test_recovery(self) -> None:
        e = EdgeNode(status=NFStatus.FAILED)
        events = e.advance(FakeRng(0.0), ctx(tick=2))
        assert any(isinstance(ev, NfRecoveredEvent) for ev in events)


# ===========================================================================
# PCF smoke tests
# ===========================================================================
class TestPCF:
    def test_apply_policy(self) -> None:
        pcf = PCF()
        result = pcf.handle("pcf.policy.apply",
                             {"scope": "Delhi", "qos_rule": "priority"})
        assert result["applied"] is True
        assert "policy_id" in result

    def test_get_policy(self) -> None:
        pcf = PCF()
        pcf.handle("pcf.policy.apply",
                   {"scope": "Delhi", "qos_rule": "premium"})
        result = pcf.handle("pcf.policy.get", {"scope": "Delhi"})
        assert len(result["policies"]) == 1

    def test_list_policies(self) -> None:
        pcf = PCF()
        pcf.handle("pcf.policy.apply", {"scope": "all"})
        result = pcf.handle("pcf.policy.list", {})
        assert result["count"] == 1


# ===========================================================================
# UDM smoke tests
# ===========================================================================
class TestUDM:
    def test_get_synthetic_subscriber(self) -> None:
        udm = UDM()
        result = udm.handle("udm.subscriber.get", {"ue_id": "ue_0001"})
        assert result["found"] is True

    def test_unknown_subscriber(self) -> None:
        udm = UDM()
        result = udm.handle("udm.subscriber.get", {"ue_id": "ue_9999"})
        assert result["found"] is False

    def test_subscriber_count(self) -> None:
        udm = UDM()
        assert udm.subscriber_count == 200


# ===========================================================================
# NEF smoke tests
# ===========================================================================
class TestNEF:
    def test_qos_request(self) -> None:
        nef = NEF()
        result = nef.handle("nef.qos.request",
                             {"flow": "video", "target_qos": "premium"})
        assert result["status"] == "accepted"

    def test_event_subscribe(self) -> None:
        nef = NEF()
        result = nef.handle("nef.event.subscribe",
                             {"event_type": "congestion"})
        assert "subscription_id" in result


# ===========================================================================
# AF smoke tests
# ===========================================================================
class TestAF:
    def test_demand_raise(self) -> None:
        af = AF()
        result = af.handle("af.demand.raise", {"qos_target": "low-latency"})
        assert result["demand_raised"] is True


# ===========================================================================
# GNB smoke tests
# ===========================================================================
class TestGNB:
    def test_attach_and_detach(self) -> None:
        gnb = GNB()
        gnb.attach_ue("ue_001")
        assert gnb.ue_count == 1
        gnb.detach_ue("ue_001")
        assert gnb.ue_count == 0

    def test_metrics(self) -> None:
        gnb = GNB()
        result = gnb.handle("gnb.metrics.get", {})
        assert "prb_utilization" in result

    def test_advance_emits_kpi(self) -> None:
        gnb = GNB()
        events = gnb.advance(FakeRng(0.5), ctx(tick=1))
        assert any(isinstance(e, KpiUpdatedEvent) for e in events)


# ===========================================================================
# UE smoke tests
# ===========================================================================
class TestUE:
    def test_advance_attaches_to_gnb(self) -> None:
        ue = UE(nf_id="ue_0001", region=Region.DELHI)
        events = ue.advance(FakeRng(0.5), ctx(tick=1))
        assert ue.attached_gnb is not None
        assert any(isinstance(e, UeAttachedEvent) for e in events)

    def test_traffic_demand_positive(self) -> None:
        ue = UE()
        ue.advance(FakeRng(0.5), ctx(tick=1))
        assert ue.traffic_demand_mbps > 0

    def test_ue_does_not_produce_services(self) -> None:
        ue = UE()
        with pytest.raises(ValueError):
            ue.handle("any.service", {})
