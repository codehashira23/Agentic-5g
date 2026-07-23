"""
C043: Unit tests for NetworkFunction base, RngStream, and AdvanceContext.

Uses a minimal concrete subclass (StubNF) to exercise the abstract base
without any real NF logic — proving the contract, not the behaviour.
"""
from __future__ import annotations

from typing import Any

import pytest
from app.domain.twin.entities import AdvanceContext, NetworkFunction, RngStream
from app.domain.twin.events import DomainEvent, NfFailedEvent, NfRecoveredEvent
from app.domain.twin.kpi import KpiName, KpiSet
from app.domain.twin.profile import NFStatus, NFType, Region


# ---------------------------------------------------------------------------
# FakeRng — deterministic stand-in for tests (no real randomness needed)
# ---------------------------------------------------------------------------
class FakeRng:
    """Deterministic RngStream for unit tests. Returns fixed values."""

    def __init__(self, fixed: float = 0.5) -> None:
        self._fixed = fixed

    def random(self) -> float:
        return self._fixed

    def gauss(self, mu: float, sigma: float) -> float:
        return mu  # always return the mean

    def uniform(self, lo: float, hi: float) -> float:
        return (lo + hi) / 2.0  # midpoint


# ---------------------------------------------------------------------------
# StubNF — minimal concrete subclass used only in tests
# ---------------------------------------------------------------------------
class StubNF(NetworkFunction):
    """
    The simplest possible NetworkFunction implementation.
    advance() does nothing; handle() only supports 'stub.ping'.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.advance_call_count = 0

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        self.advance_call_count += 1
        return []   # no events by default

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if service_name == "stub.ping":
            return {"pong": True}
        raise self._unsupported(service_name)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------
def make_stub(
    nf_id: str = "stub_core_1",
    nf_type: NFType = NFType.AMF,
    region: Region = Region.CORE,
    status: NFStatus = NFStatus.ACTIVE,
    load: float = 0.0,
) -> StubNF:
    return StubNF(nf_id=nf_id, nf_type=nf_type, region=region, status=status, load=load)


def make_ctx(tick: int = 1, demand: float = 1.0) -> AdvanceContext:
    return AdvanceContext(tick=tick, demand_factor=demand)


def make_rng(fixed: float = 0.5) -> FakeRng:
    return FakeRng(fixed=fixed)


# ---------------------------------------------------------------------------
# RngStream protocol conformance
# ---------------------------------------------------------------------------
class TestRngStreamProtocol:
    def test_fake_rng_satisfies_protocol(self) -> None:
        rng = FakeRng()
        assert isinstance(rng, RngStream)

    def test_random_returns_fixed_value(self) -> None:
        rng = FakeRng(fixed=0.3)
        assert rng.random() == 0.3

    def test_gauss_returns_mean(self) -> None:
        rng = FakeRng()
        assert rng.gauss(10.0, 2.0) == 10.0

    def test_uniform_returns_midpoint(self) -> None:
        rng = FakeRng()
        assert rng.uniform(0.0, 1.0) == 0.5


# ---------------------------------------------------------------------------
# AdvanceContext
# ---------------------------------------------------------------------------
class TestAdvanceContext:
    def test_construction(self) -> None:
        ctx = AdvanceContext(tick=5)
        assert ctx.tick == 5
        assert ctx.demand_factor == 1.0
        assert ctx.connected_nf_ids == frozenset()

    def test_tick_must_be_non_negative(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AdvanceContext(tick=-1)

    def test_immutable(self) -> None:
        from pydantic import ValidationError
        ctx = AdvanceContext(tick=1)
        with pytest.raises(ValidationError):
            ctx.tick = 99  # type: ignore[misc]

    def test_connected_nf_ids(self) -> None:
        ctx = AdvanceContext(tick=1, connected_nf_ids=frozenset(["amf_1", "smf_1"]))
        assert "amf_1" in ctx.connected_nf_ids


# ---------------------------------------------------------------------------
# NetworkFunction — construction and public properties
# ---------------------------------------------------------------------------
class TestNetworkFunctionConstruction:
    def test_profile_set_correctly(self) -> None:
        nf = make_stub(nf_id="amf_core_1", nf_type=NFType.AMF, region=Region.CORE)
        assert nf.id == "amf_core_1"
        assert nf.nf_type == NFType.AMF
        assert nf.region == Region.CORE

    def test_default_status_is_active(self) -> None:
        nf = make_stub()
        assert nf.status == NFStatus.ACTIVE

    def test_default_load_is_zero(self) -> None:
        nf = make_stub()
        assert nf.load == 0.0

    def test_load_clamped_above(self) -> None:
        nf = make_stub(load=2.5)
        assert nf.load == 1.0

    def test_load_clamped_below(self) -> None:
        nf = make_stub(load=-0.5)
        assert nf.load == 0.0

    def test_kpis_empty_by_default(self) -> None:
        nf = make_stub()
        assert nf.kpis == {}

    def test_repr_contains_id_and_status(self) -> None:
        nf = make_stub(nf_id="amf_1")
        r = repr(nf)
        assert "amf_1" in r
        assert "ACTIVE" in r


# ---------------------------------------------------------------------------
# NetworkFunction — is_healthy
# ---------------------------------------------------------------------------
class TestNetworkFunctionIsHealthy:
    def test_active_is_healthy(self) -> None:
        nf = make_stub(status=NFStatus.ACTIVE)
        assert nf.is_healthy() is True

    def test_standby_is_healthy(self) -> None:
        nf = make_stub(status=NFStatus.STANDBY)
        assert nf.is_healthy() is True

    def test_failed_is_not_healthy(self) -> None:
        nf = make_stub(status=NFStatus.FAILED)
        assert nf.is_healthy() is False

    def test_degraded_is_not_healthy(self) -> None:
        nf = make_stub(status=NFStatus.DEGRADED)
        assert nf.is_healthy() is False


# ---------------------------------------------------------------------------
# NetworkFunction — advance contract
# ---------------------------------------------------------------------------
class TestNetworkFunctionAdvance:
    def test_advance_is_called(self) -> None:
        nf = make_stub()
        nf.advance(make_rng(), make_ctx(tick=1))
        assert nf.advance_call_count == 1

    def test_advance_multiple_ticks(self) -> None:
        nf = make_stub()
        for tick in range(1, 6):
            nf.advance(make_rng(), make_ctx(tick=tick))
        assert nf.advance_call_count == 5

    def test_advance_returns_list(self) -> None:
        nf = make_stub()
        result = nf.advance(make_rng(), make_ctx())
        assert isinstance(result, list)

    def test_advance_returns_empty_for_stub(self) -> None:
        nf = make_stub()
        events = nf.advance(make_rng(), make_ctx())
        assert events == []

    def test_advance_deterministic_with_same_rng(self) -> None:
        """Two NFs with same initial state + same FakeRng → same results."""
        nf1 = make_stub()
        nf2 = make_stub()
        e1 = nf1.advance(FakeRng(0.3), make_ctx(tick=1))
        e2 = nf2.advance(FakeRng(0.3), make_ctx(tick=1))
        assert e1 == e2


# ---------------------------------------------------------------------------
# NetworkFunction — handle contract
# ---------------------------------------------------------------------------
class TestNetworkFunctionHandle:
    def test_supported_service_returns_result(self) -> None:
        nf = make_stub()
        result = nf.handle("stub.ping", {})
        assert result == {"pong": True}

    def test_unsupported_service_raises_value_error(self) -> None:
        nf = make_stub()
        with pytest.raises(ValueError, match="stub.unknown"):
            nf.handle("stub.unknown", {})

    def test_error_message_contains_nf_id(self) -> None:
        nf = make_stub(nf_id="amf_core_1")
        with pytest.raises(ValueError, match="amf_core_1"):
            nf.handle("nrf.discover", {})


# ---------------------------------------------------------------------------
# NetworkFunction — protected helpers (_set_status, _set_load, _set_kpi)
# ---------------------------------------------------------------------------
class TestNetworkFunctionHelpers:
    def test_set_status_updates_profile(self) -> None:
        nf = make_stub()
        nf._set_status(NFStatus.FAILED)
        assert nf.status == NFStatus.FAILED

    def test_set_status_preserves_other_profile_fields(self) -> None:
        nf = make_stub(nf_id="amf_1", nf_type=NFType.AMF, region=Region.DELHI)
        nf._set_status(NFStatus.RECOVERING)
        assert nf.id == "amf_1"
        assert nf.nf_type == NFType.AMF

    def test_set_load_updates_load(self) -> None:
        nf = make_stub()
        nf._set_load(0.75)
        assert nf.load == 0.75

    def test_set_load_clamped(self) -> None:
        nf = make_stub()
        nf._set_load(5.0)
        assert nf.load == 1.0

    def test_set_kpi_stores_kpi_set(self) -> None:
        nf = make_stub()
        k = KpiSet.for_latency()
        k = k.update(18.0)
        nf._set_kpi(k)
        assert KpiName.LATENCY_MS in nf.kpis
        assert nf.kpis[KpiName.LATENCY_MS].current == 18.0

    def test_get_kpi_returns_zero_default(self) -> None:
        nf = make_stub()
        k = nf._get_kpi(KpiName.LATENCY_MS)
        assert k.current == 0.0

    def test_get_kpi_returns_stored_value(self) -> None:
        nf = make_stub()
        k = KpiSet.for_latency().update(12.5)
        nf._set_kpi(k)
        assert nf._get_kpi(KpiName.LATENCY_MS).current == 12.5

    def test_kpis_property_returns_copy(self) -> None:
        """Mutating the returned dict must NOT affect the NF's internal state."""
        nf = make_stub()
        snapshot = nf.kpis
        snapshot[KpiName.LATENCY_MS] = KpiSet(name=KpiName.LATENCY_MS)
        assert KpiName.LATENCY_MS not in nf.kpis


# ---------------------------------------------------------------------------
# Subclass can emit events from advance()
# (proves the event-return contract works end-to-end)
# ---------------------------------------------------------------------------
class EventEmittingNF(NetworkFunction):
    """NF that emits an NfFailedEvent if rng.random() > 0.9."""

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        if rng.random() > 0.9:
            self._set_status(NFStatus.FAILED)
            return [NfFailedEvent(entity_id=self.id, nf_type=self.nf_type.value)]
        return []

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise self._unsupported(service_name)


class EventEmittingRecoveringNF(NetworkFunction):
    """NF that transitions FAILED → RECOVERING → ACTIVE over 2 ticks."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tick_failed = -1

    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        if self.status == NFStatus.ACTIVE and rng.random() > 0.9:
            self._set_status(NFStatus.FAILED)
            self._tick_failed = ctx.tick
            return [NfFailedEvent(entity_id=self.id, nf_type=self.nf_type.value)]
        if self.status == NFStatus.FAILED and ctx.tick >= self._tick_failed + 2:
            self._set_status(NFStatus.ACTIVE)
            return [NfRecoveredEvent(entity_id=self.id, nf_type=self.nf_type.value)]
        return []

    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise self._unsupported(service_name)


class TestNFEventEmission:
    def test_no_event_when_rng_below_threshold(self) -> None:
        nf = EventEmittingNF(
            nf_id="upf_1", nf_type=NFType.UPF, region=Region.DELHI
        )
        events = nf.advance(FakeRng(fixed=0.5), make_ctx(tick=1))
        assert events == []
        assert nf.status == NFStatus.ACTIVE

    def test_fail_event_when_rng_above_threshold(self) -> None:
        nf = EventEmittingNF(
            nf_id="upf_1", nf_type=NFType.UPF, region=Region.DELHI
        )
        events = nf.advance(FakeRng(fixed=0.99), make_ctx(tick=1))
        assert len(events) == 1
        assert isinstance(events[0], NfFailedEvent)
        assert events[0].entity_id == "upf_1"
        assert nf.status == NFStatus.FAILED

    def test_recovery_cycle(self) -> None:
        nf = EventEmittingRecoveringNF(
            nf_id="upf_1", nf_type=NFType.UPF, region=Region.DELHI
        )
        # Tick 1: rng=0.99 → fails
        events_t1 = nf.advance(FakeRng(0.99), make_ctx(tick=1))
        assert nf.status == NFStatus.FAILED
        assert any(isinstance(e, NfFailedEvent) for e in events_t1)

        # Tick 2: still failed (only 1 tick since failure, need 2)
        events_t2 = nf.advance(FakeRng(0.0), make_ctx(tick=2))
        assert nf.status == NFStatus.FAILED
        assert events_t2 == []

        # Tick 3: tick >= failed_tick + 2 → recovers
        events_t3 = nf.advance(FakeRng(0.0), make_ctx(tick=3))
        assert nf.status == NFStatus.ACTIVE
        assert any(isinstance(e, NfRecoveredEvent) for e in events_t3)
