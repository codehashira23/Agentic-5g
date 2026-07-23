"""
C045: Unit tests for AMF, SMF, and UPF entities.
"""
from __future__ import annotations

import pytest
from app.domain.twin.entities import AdvanceContext
from app.domain.twin.events import (
    KpiUpdatedEvent,
    NfFailedEvent,
    NfRecoveredEvent,
)
from app.domain.twin.kpi import KpiName
from app.domain.twin.nf.amf import AMF
from app.domain.twin.nf.smf import SMF
from app.domain.twin.nf.upf import UPF
from app.domain.twin.profile import NFStatus, NFType


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
# AMF
# ===========================================================================
class TestAMFConstruction:
    def test_defaults(self) -> None:
        amf = AMF()
        assert amf.id == "amf_core_1"
        assert amf.nf_type == NFType.AMF
        assert amf.status == NFStatus.ACTIVE
        assert amf.ue_count == 0

    def test_produces_services(self) -> None:
        amf = AMF()
        assert "amf.ue.register" in amf.profile.services
        assert "amf.ue.deregister" in amf.profile.services
        assert "amf.ue.context.get" in amf.profile.services


class TestAMFUERegistration:
    def test_register_ue(self) -> None:
        amf = AMF()
        result = amf.handle("amf.ue.register", {"ue_id": "ue_001"})
        assert result["registered"] is True
        assert amf.ue_count == 1

    def test_register_multiple_ues(self) -> None:
        amf = AMF()
        for i in range(5):
            amf.handle("amf.ue.register", {"ue_id": f"ue_{i:03d}"})
        assert amf.ue_count == 5

    def test_deregister_ue(self) -> None:
        amf = AMF()
        amf.handle("amf.ue.register", {"ue_id": "ue_001"})
        result = amf.handle("amf.ue.deregister", {"ue_id": "ue_001"})
        assert result["deregistered"] is True
        assert amf.ue_count == 0

    def test_deregister_unknown_ue(self) -> None:
        amf = AMF()
        result = amf.handle("amf.ue.deregister", {"ue_id": "ue_999"})
        assert result["deregistered"] is False

    def test_get_context_registered_ue(self) -> None:
        amf = AMF()
        amf.handle("amf.ue.register", {"ue_id": "ue_001"})
        result = amf.handle("amf.ue.context.get", {"ue_id": "ue_001"})
        assert result["found"] is True
        assert result["ue_id"] == "ue_001"

    def test_get_context_unknown_ue(self) -> None:
        amf = AMF()
        result = amf.handle("amf.ue.context.get", {"ue_id": "ue_999"})
        assert result["found"] is False

    def test_registered_ues_is_frozen_copy(self) -> None:
        amf = AMF()
        amf.handle("amf.ue.register", {"ue_id": "ue_001"})
        snapshot = amf.registered_ues
        assert isinstance(snapshot, frozenset)


class TestAMFAdvance:
    def test_emits_kpi_updated(self) -> None:
        amf = AMF()
        events = amf.advance(FakeRng(0.5), ctx(tick=1))
        kpi_events = [e for e in events if isinstance(e, KpiUpdatedEvent)]
        assert len(kpi_events) >= 1

    def test_failure_on_low_rng(self) -> None:
        amf = AMF()
        events = amf.advance(FakeRng(0.0), ctx(tick=1))
        assert any(isinstance(e, NfFailedEvent) for e in events)
        assert amf.status == NFStatus.FAILED

    def test_recovery_from_failed(self) -> None:
        amf = AMF(status=NFStatus.FAILED)
        events = amf.advance(FakeRng(0.0), ctx(tick=2))
        assert any(isinstance(e, NfRecoveredEvent) for e in events)
        assert amf.status == NFStatus.ACTIVE

    def test_unsupported_service(self) -> None:
        amf = AMF()
        with pytest.raises(ValueError, match="amf_core_1"):
            amf.handle("nrf.discover", {})


# ===========================================================================
# SMF
# ===========================================================================
class TestSMFConstruction:
    def test_defaults(self) -> None:
        smf = SMF()
        assert smf.id == "smf_core_1"
        assert smf.nf_type == NFType.SMF
        assert smf.session_count == 0

    def test_produces_services(self) -> None:
        smf = SMF()
        for svc in ("smf.session.create", "smf.session.modify",
                     "smf.session.release", "smf.session.list"):
            assert svc in smf.profile.services


class TestSMFSessions:
    def test_create_session(self) -> None:
        smf = SMF()
        result = smf.handle("smf.session.create", {"ue_id": "ue_001"})
        assert "session_id" in result
        assert result["ue_id"] == "ue_001"
        assert smf.session_count == 1

    def test_create_session_default_upf(self) -> None:
        smf = SMF()
        result = smf.handle("smf.session.create", {"ue_id": "ue_001"})
        assert result["upf_id"] == "upf_core_1"

    def test_create_session_custom_qos(self) -> None:
        smf = SMF()
        result = smf.handle("smf.session.create", {
            "ue_id": "ue_001", "qos_class": "premium"
        })
        assert result["qos_class"] == "premium"

    def test_modify_session(self) -> None:
        smf = SMF()
        create = smf.handle("smf.session.create", {"ue_id": "ue_001"})
        sess_id = create["session_id"]
        result = smf.handle("smf.session.modify", {
            "session_id": sess_id, "qos_class": "premium"
        })
        assert result["modified"] is True
        assert smf.sessions[sess_id]["qos_class"] == "premium"

    def test_modify_unknown_session(self) -> None:
        smf = SMF()
        result = smf.handle("smf.session.modify", {
            "session_id": "nonexistent", "qos_class": "premium"
        })
        assert result["modified"] is False

    def test_release_session(self) -> None:
        smf = SMF()
        create = smf.handle("smf.session.create", {"ue_id": "ue_001"})
        sess_id = create["session_id"]
        result = smf.handle("smf.session.release", {"session_id": sess_id})
        assert result["released"] is True
        assert smf.session_count == 0

    def test_release_unknown_session(self) -> None:
        smf = SMF()
        result = smf.handle("smf.session.release", {"session_id": "nope"})
        assert result["released"] is False

    def test_list_sessions_by_ue(self) -> None:
        smf = SMF()
        smf.handle("smf.session.create", {"ue_id": "ue_001"})
        smf.handle("smf.session.create", {"ue_id": "ue_001"})
        smf.handle("smf.session.create", {"ue_id": "ue_002"})
        result = smf.handle("smf.session.list", {"ue_id": "ue_001"})
        assert result["count"] == 2

    def test_list_all_sessions(self) -> None:
        smf = SMF()
        for i in range(3):
            smf.handle("smf.session.create", {"ue_id": f"ue_{i}"})
        result = smf.handle("smf.session.list", {})
        assert result["count"] == 3


class TestSMFAdvance:
    def test_emits_kpi_updated(self) -> None:
        smf = SMF()
        events = smf.advance(FakeRng(0.5), ctx(tick=1))
        kpi_events = [e for e in events if isinstance(e, KpiUpdatedEvent)]
        assert len(kpi_events) >= 1

    def test_failure_on_low_rng(self) -> None:
        smf = SMF()
        events = smf.advance(FakeRng(0.0), ctx(tick=1))
        assert any(isinstance(e, NfFailedEvent) for e in events)
        assert smf.status == NFStatus.FAILED

    def test_recovery_from_failed(self) -> None:
        smf = SMF(status=NFStatus.FAILED)
        events = smf.advance(FakeRng(0.0), ctx(tick=2))
        assert any(isinstance(e, NfRecoveredEvent) for e in events)

    def test_unsupported_service(self) -> None:
        smf = SMF()
        with pytest.raises(ValueError):
            smf.handle("nrf.discover", {})


# ===========================================================================
# UPF
# ===========================================================================
class TestUPFConstruction:
    def test_defaults(self) -> None:
        upf = UPF()
        assert upf.id == "upf_core_1"
        assert upf.nf_type == NFType.UPF
        assert upf.session_count == 0

    def test_produces_services(self) -> None:
        upf = UPF()
        for svc in ("upf.session.install", "upf.session.remove",
                     "upf.loadbalance.apply", "upf.metrics.get"):
            assert svc in upf.profile.services

    def test_latency_kpi_has_thresholds(self) -> None:
        upf = UPF()
        lat_kpi = upf.kpis[KpiName.LATENCY_MS]
        assert lat_kpi.high_threshold == 20.0
        assert lat_kpi.low_threshold == 15.0


class TestUPFSessions:
    def test_install_session(self) -> None:
        upf = UPF()
        result = upf.handle("upf.session.install", {"session_id": "sess_001"})
        assert result["installed"] is True
        assert upf.session_count == 1

    def test_remove_session(self) -> None:
        upf = UPF()
        upf.handle("upf.session.install", {"session_id": "sess_001"})
        result = upf.handle("upf.session.remove", {"session_id": "sess_001"})
        assert result["removed"] is True
        assert upf.session_count == 0

    def test_remove_unknown_session(self) -> None:
        upf = UPF()
        result = upf.handle("upf.session.remove", {"session_id": "nope"})
        assert result["removed"] is False


class TestUPFLoadBalance:
    def test_loadbalance_reduces_sessions(self) -> None:
        upf = UPF()
        for i in range(10):
            upf.handle("upf.session.install", {"session_id": f"sess_{i}"})
        result = upf.handle("upf.loadbalance.apply", {"fraction": 0.5})
        assert result["moved_count"] == 5
        assert upf.session_count == 5

    def test_loadbalance_zero_fraction(self) -> None:
        upf = UPF()
        for i in range(4):
            upf.handle("upf.session.install", {"session_id": f"s_{i}"})
        result = upf.handle("upf.loadbalance.apply", {"fraction": 0.0})
        assert result["moved_count"] == 0
        assert upf.session_count == 4

    def test_loadbalance_full_fraction(self) -> None:
        upf = UPF()
        for i in range(4):
            upf.handle("upf.session.install", {"session_id": f"s_{i}"})
        result = upf.handle("upf.loadbalance.apply", {"fraction": 1.0})
        assert result["moved_count"] == 4
        assert upf.session_count == 0


class TestUPFMetrics:
    def test_get_metrics_returns_expected_keys(self) -> None:
        upf = UPF()
        result = upf.handle("upf.metrics.get", {})
        for key in ("latency_ms", "throughput_mbps", "packet_loss",
                     "session_count", "load"):
            assert key in result

    def test_latency_at_zero_load_is_near_base(self) -> None:
        """With no sessions, latency ≈ base_latency (5 ms)."""
        upf = UPF(base_latency_ms=5.0)
        upf.advance(FakeRng(0.5), ctx(tick=1))   # gauss returns mu=0 → no noise
        assert upf.latency_ms < 10.0


class TestUPFAdvance:
    def test_emits_three_kpi_events(self) -> None:
        upf = UPF()
        events = upf.advance(FakeRng(0.5), ctx(tick=1))
        kpi_events = [e for e in events if isinstance(e, KpiUpdatedEvent)]
        assert len(kpi_events) == 3

    def test_kpi_names_correct(self) -> None:
        upf = UPF()
        events = upf.advance(FakeRng(0.5), ctx(tick=1))
        kpi_names = {
            e.kpi for e in events if isinstance(e, KpiUpdatedEvent)
        }
        assert "latency_ms" in kpi_names
        assert "throughput_mbps" in kpi_names
        assert "packet_loss" in kpi_names

    def test_failure_on_low_rng(self) -> None:
        upf = UPF()
        events = upf.advance(FakeRng(0.0), ctx(tick=1))
        assert any(isinstance(e, NfFailedEvent) for e in events)
        assert upf.status == NFStatus.FAILED

    def test_no_kpi_events_on_failure_tick(self) -> None:
        upf = UPF()
        events = upf.advance(FakeRng(0.0), ctx(tick=1))
        kpi_events = [e for e in events if isinstance(e, KpiUpdatedEvent)]
        assert kpi_events == []

    def test_recovery_from_failed(self) -> None:
        upf = UPF(status=NFStatus.FAILED)
        events = upf.advance(FakeRng(0.0), ctx(tick=2))
        assert any(isinstance(e, NfRecoveredEvent) for e in events)

    def test_load_increases_with_sessions(self) -> None:
        upf = UPF()
        # install 250 sessions (half of MAX_SESSIONS=500)
        for i in range(250):
            upf.handle("upf.session.install", {"session_id": f"s_{i}"})
        upf.advance(FakeRng(0.5), ctx(tick=1))
        assert upf.load >= 0.4   # utilisation should be noticeable

    def test_latency_rises_under_high_load(self) -> None:
        upf = UPF()
        # Install near-max sessions to drive utilisation high
        for i in range(490):
            upf.handle("upf.session.install", {"session_id": f"s_{i}"})
        upf.advance(FakeRng(0.5), ctx(tick=1))
        assert upf.latency_ms > 10.0   # latency must be above base

    def test_unsupported_service(self) -> None:
        upf = UPF()
        with pytest.raises(ValueError):
            upf.handle("nrf.discover", {})
