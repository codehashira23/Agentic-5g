"""
C044: Unit tests for the NRF (Network Repository Function) entity.

Covers:
  - Construction and defaults
  - nrf.register  (idempotent)
  - nrf.deregister (with PLC-1 domain invariant)
  - nrf.discover  (filters: type, region, status)
  - nrf.list
  - advance() — KPI update, stochastic failure, auto-recovery
  - Standby promotion
  - Unsupported service raises
"""
from __future__ import annotations

import pytest
from app.domain.twin.events import (
    KpiUpdatedEvent,
    NfFailedEvent,
    NfRecoveredEvent,
)
from app.domain.twin.nf.nrf import NRF
from app.domain.twin.profile import NFProfile, NFStatus, NFType, Region


# ---------------------------------------------------------------------------
# Re-use FakeRng from the base tests (inline here to keep tests self-contained)
# ---------------------------------------------------------------------------
class FakeRng:
    def __init__(self, fixed: float = 0.5) -> None:
        self._fixed = fixed

    def random(self) -> float:
        return self._fixed

    def gauss(self, mu: float, sigma: float) -> float:
        return mu

    def uniform(self, lo: float, hi: float) -> float:
        return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
from app.domain.twin.entities import AdvanceContext  # noqa: E402


def make_ctx(tick: int = 1, demand: float = 1.0) -> AdvanceContext:
    return AdvanceContext(tick=tick, demand_factor=demand)


def make_profile(
    nf_id: str = "amf_core_1",
    nf_type: NFType = NFType.AMF,
    region: Region = Region.CORE,
    status: NFStatus = NFStatus.ACTIVE,
) -> NFProfile:
    return NFProfile(id=nf_id, type=nf_type, region=region, status=status)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
class TestNRFConstruction:
    def test_default_id_and_type(self) -> None:
        nrf = NRF()
        assert nrf.id == "nrf_core_1"
        assert nrf.nf_type == NFType.NRF

    def test_default_status_active(self) -> None:
        nrf = NRF()
        assert nrf.status == NFStatus.ACTIVE

    def test_registry_empty_on_start(self) -> None:
        nrf = NRF()
        assert nrf.registered_count == 0

    def test_produces_four_services(self) -> None:
        nrf = NRF()
        assert "nrf.register" in nrf.profile.services
        assert "nrf.deregister" in nrf.profile.services
        assert "nrf.discover" in nrf.profile.services
        assert "nrf.list" in nrf.profile.services

    def test_standby_flag(self) -> None:
        nrf = NRF(nf_id="nrf_standby_1", is_standby=True, status=NFStatus.STANDBY)
        assert nrf.is_standby is True
        assert nrf.status == NFStatus.STANDBY


# ---------------------------------------------------------------------------
# nrf.register
# ---------------------------------------------------------------------------
class TestNRFRegister:
    def test_register_adds_to_registry(self) -> None:
        nrf = NRF()
        p = make_profile("amf_1", NFType.AMF)
        result = nrf.handle("nrf.register", {"profile": p.model_dump()})
        assert result["registered"] is True
        assert nrf.registered_count == 1

    def test_register_idempotent(self) -> None:
        """Re-registering the same id replaces the old entry."""
        nrf = NRF()
        p = make_profile("amf_1", NFType.AMF)
        nrf.handle("nrf.register", {"profile": p.model_dump()})
        nrf.handle("nrf.register", {"profile": p.model_dump()})
        assert nrf.registered_count == 1

    def test_register_multiple_nfs(self) -> None:
        nrf = NRF()
        for nf_id, nf_type in [("amf_1", NFType.AMF), ("smf_1", NFType.SMF), ("upf_1", NFType.UPF)]:
            nrf.handle("nrf.register", {"profile": make_profile(nf_id, nf_type).model_dump()})
        assert nrf.registered_count == 3

    def test_registered_profile_retrievable(self) -> None:
        nrf = NRF()
        p = make_profile("amf_1", NFType.AMF)
        nrf.handle("nrf.register", {"profile": p.model_dump()})
        assert "amf_1" in nrf.registry


# ---------------------------------------------------------------------------
# nrf.deregister
# ---------------------------------------------------------------------------
class TestNRFDeregister:
    def test_deregister_removes_nf(self) -> None:
        nrf = NRF()
        p = make_profile("amf_1", NFType.AMF)
        nrf.handle("nrf.register", {"profile": p.model_dump()})
        result = nrf.handle("nrf.deregister", {"nf_id": "amf_1"})
        assert result["deregistered"] is True
        assert nrf.registered_count == 0

    def test_deregister_unknown_id_returns_false(self) -> None:
        nrf = NRF()
        result = nrf.handle("nrf.deregister", {"nf_id": "nonexistent"})
        assert result["deregistered"] is False

    def test_plc1_blocks_last_nrf_deregister(self) -> None:
        """
        PLC-1 domain invariant: cannot deregister the last active NRF.
        This is the defence-in-depth guard (07-network-core.md §6.6).
        """
        nrf = NRF(nf_id="nrf_core_1")
        # Register nrf_core_1 itself so it appears in its own registry
        nrf.handle("nrf.register", {"profile": nrf.profile.model_dump()})
        with pytest.raises(ValueError, match="PLC-1"):
            nrf.handle("nrf.deregister", {"nf_id": "nrf_core_1"})

    def test_plc1_allows_deregister_when_another_nrf_remains(self) -> None:
        """Two NRFs registered → deregistering one is fine."""
        nrf = NRF(nf_id="nrf_core_1")
        nrf.handle("nrf.register", {"profile": nrf.profile.model_dump()})
        nrf2_profile = NFProfile(
            id="nrf_core_2",
            type=NFType.NRF,
            region=Region.CORE,
            status=NFStatus.ACTIVE,
        )
        nrf.handle("nrf.register", {"profile": nrf2_profile.model_dump()})
        result = nrf.handle("nrf.deregister", {"nf_id": "nrf_core_1"})
        assert result["deregistered"] is True

    def test_plc1_does_not_block_non_nrf_types(self) -> None:
        """PLC-1 only applies to NRF-type NFs — other types can be fully removed."""
        nrf = NRF()
        p = make_profile("amf_1", NFType.AMF)
        nrf.handle("nrf.register", {"profile": p.model_dump()})
        result = nrf.handle("nrf.deregister", {"nf_id": "amf_1"})
        assert result["deregistered"] is True


# ---------------------------------------------------------------------------
# nrf.discover
# ---------------------------------------------------------------------------
class TestNRFDiscover:
    def _populated_nrf(self) -> NRF:
        nrf = NRF()
        profiles = [
            make_profile("amf_delhi_1", NFType.AMF, Region.DELHI),
            make_profile("amf_mumbai_1", NFType.AMF, Region.MUMBAI),
            make_profile("smf_core_1", NFType.SMF, Region.CORE),
            make_profile("upf_delhi_1", NFType.UPF, Region.DELHI),
            make_profile("upf_delhi_2", NFType.UPF, Region.DELHI,
                         status=NFStatus.FAILED),   # failed — filtered by default
        ]
        for p in profiles:
            nrf.handle("nrf.register", {"profile": p.model_dump()})
        return nrf

    def test_discover_all_active(self) -> None:
        nrf = self._populated_nrf()
        result = nrf.handle("nrf.discover", {})
        # 4 active profiles (upf_delhi_2 is FAILED, filtered out)
        assert result["count"] == 4

    def test_discover_by_type(self) -> None:
        nrf = self._populated_nrf()
        result = nrf.handle("nrf.discover", {"nf_type": "AMF"})
        assert result["count"] == 2
        assert all(p["type"] == "AMF" for p in result["profiles"])

    def test_discover_by_region(self) -> None:
        nrf = self._populated_nrf()
        result = nrf.handle("nrf.discover", {"region": "Delhi"})
        # amf_delhi_1 + upf_delhi_1 (upf_delhi_2 is FAILED)
        assert result["count"] == 2

    def test_discover_by_type_and_region(self) -> None:
        nrf = self._populated_nrf()
        result = nrf.handle("nrf.discover", {"nf_type": "UPF", "region": "Delhi"})
        assert result["count"] == 1
        assert result["profiles"][0]["id"] == "upf_delhi_1"

    def test_discover_failed_status_filter(self) -> None:
        nrf = self._populated_nrf()
        result = nrf.handle("nrf.discover", {"status": "FAILED"})
        assert result["count"] == 1
        assert result["profiles"][0]["id"] == "upf_delhi_2"

    def test_discover_no_match_returns_empty(self) -> None:
        nrf = self._populated_nrf()
        result = nrf.handle("nrf.discover", {"nf_type": "NWDAF"})
        assert result["count"] == 0
        assert result["profiles"] == []


# ---------------------------------------------------------------------------
# nrf.list
# ---------------------------------------------------------------------------
class TestNRFList:
    def test_list_returns_all_including_failed(self) -> None:
        nrf = NRF()
        nrf.handle("nrf.register", {
            "profile": make_profile("amf_1", NFType.AMF).model_dump()
        })
        nrf.handle("nrf.register", {
            "profile": make_profile("upf_1", NFType.UPF,
                                    status=NFStatus.FAILED).model_dump()
        })
        result = nrf.handle("nrf.list", {})
        assert result["count"] == 2


# ---------------------------------------------------------------------------
# advance() — KPI update
# ---------------------------------------------------------------------------
class TestNRFAdvanceKPI:
    def test_advance_emits_kpi_updated(self) -> None:
        nrf = NRF()
        events = nrf.advance(FakeRng(fixed=0.5), make_ctx(tick=1))
        kpi_events = [e for e in events if isinstance(e, KpiUpdatedEvent)]
        assert len(kpi_events) == 1
        assert kpi_events[0].kpi == "discovery_rate"

    def test_kpi_value_is_non_negative(self) -> None:
        nrf = NRF()
        nrf.advance(FakeRng(fixed=0.5), make_ctx(tick=1))
        from app.domain.twin.kpi import KpiName
        assert nrf.kpis[KpiName.DISCOVERY_RATE].current >= 0.0

    def test_advance_multiple_ticks_accumulates_ema(self) -> None:
        nrf = NRF()
        for tick in range(1, 11):
            nrf.advance(FakeRng(fixed=0.5), make_ctx(tick=tick))
        from app.domain.twin.kpi import KpiName
        # After 10 ticks the smoothed value should be > 0
        assert nrf.kpis[KpiName.DISCOVERY_RATE].smoothed > 0.0


# ---------------------------------------------------------------------------
# advance() — stochastic failure
# ---------------------------------------------------------------------------
class TestNRFAdvanceFailure:
    def test_high_rng_triggers_failure(self) -> None:
        """rng.random() returns 0.0 < _HAZARD_PROB → fails."""
        nrf = NRF()
        # Use a value below the hazard probability (0.001)
        events = nrf.advance(FakeRng(fixed=0.0), make_ctx(tick=1))
        failed = [e for e in events if isinstance(e, NfFailedEvent)]
        assert len(failed) == 1
        assert nrf.status == NFStatus.FAILED

    def test_nf_failed_event_fields(self) -> None:
        nrf = NRF(nf_id="nrf_core_1")
        events = nrf.advance(FakeRng(fixed=0.0), make_ctx(tick=5))
        evt = next(e for e in events if isinstance(e, NfFailedEvent))
        assert evt.entity_id == "nrf_core_1"
        assert evt.cause == "hazard"
        assert evt.tick == 5

    def test_no_kpi_event_on_failure_tick(self) -> None:
        """advance() returns early on failure — no KPI event emitted."""
        nrf = NRF()
        events = nrf.advance(FakeRng(fixed=0.0), make_ctx(tick=1))
        kpi_events = [e for e in events if isinstance(e, KpiUpdatedEvent)]
        assert kpi_events == []

    def test_safe_rng_does_not_fail(self) -> None:
        nrf = NRF()
        events = nrf.advance(FakeRng(fixed=0.5), make_ctx(tick=1))
        failed = [e for e in events if isinstance(e, NfFailedEvent)]
        assert failed == []
        assert nrf.status == NFStatus.ACTIVE


# ---------------------------------------------------------------------------
# advance() — auto-recovery from FAILED
# ---------------------------------------------------------------------------
class TestNRFAdvanceRecovery:
    def test_auto_recovery_when_rng_below_threshold(self) -> None:
        """
        When FAILED and rng < _RECOVERY_PROB (0.05), the NRF auto-recovers.
        FakeRng(0.0) always returns 0.0 < 0.05 → always recovers.
        """
        nrf = NRF(status=NFStatus.FAILED)
        events = nrf.advance(FakeRng(fixed=0.0), make_ctx(tick=2))
        recovered = [e for e in events if isinstance(e, NfRecoveredEvent)]
        assert len(recovered) == 1
        assert nrf.status == NFStatus.ACTIVE

    def test_no_recovery_when_rng_above_threshold(self) -> None:
        """FakeRng(0.5) → 0.5 > 0.05 → stays FAILED."""
        nrf = NRF(status=NFStatus.FAILED)
        events = nrf.advance(FakeRng(fixed=0.5), make_ctx(tick=2))
        recovered = [e for e in events if isinstance(e, NfRecoveredEvent)]
        assert recovered == []
        assert nrf.status == NFStatus.FAILED


# ---------------------------------------------------------------------------
# Standby promotion (Scenario C — Recovery agent path)
# ---------------------------------------------------------------------------
class TestNRFStandbyPromotion:
    def test_promote_standby_sets_active(self) -> None:
        nrf = NRF(nf_id="nrf_standby_1", is_standby=True, status=NFStatus.STANDBY)
        assert nrf.status == NFStatus.STANDBY
        nrf.promote_standby()
        assert nrf.status == NFStatus.ACTIVE
        assert nrf.is_standby is False

    def test_promote_non_standby_does_nothing(self) -> None:
        """Promoting an already-active NRF should not crash or change state."""
        nrf = NRF(nf_id="nrf_core_1", is_standby=False, status=NFStatus.ACTIVE)
        nrf.promote_standby()          # no-op
        assert nrf.status == NFStatus.ACTIVE


# ---------------------------------------------------------------------------
# Unsupported service
# ---------------------------------------------------------------------------
class TestNRFUnsupportedService:
    def test_unknown_service_raises_value_error(self) -> None:
        nrf = NRF()
        with pytest.raises(ValueError, match="nrf.unknown"):
            nrf.handle("nrf.unknown", {})

    def test_error_message_contains_nf_id(self) -> None:
        nrf = NRF(nf_id="nrf_core_1")
        with pytest.raises(ValueError, match="nrf_core_1"):
            nrf.handle("amf.ue.register", {})
