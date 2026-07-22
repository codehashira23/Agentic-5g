"""
C041: Unit tests for KpiName, KpiSample, and KpiSet.
Focus: construction, physical clamping, EMA smoothing, min/max,
and the hysteresis breach/clear logic (06-digital-twin.md §8).
"""
import pytest
from app.domain.twin.kpi import KpiName, KpiSample, KpiSet
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# KpiName
# ---------------------------------------------------------------------------
class TestKpiName:
    def test_all_10_names_exist(self) -> None:
        expected = {
            "latency_ms", "throughput_mbps", "prb_utilization",
            "packet_loss", "registration_load", "session_setup_rate",
            "discovery_rate", "analytics_accuracy", "compute_load",
            "energy_index",
        }
        assert {k.value for k in KpiName} == expected

    def test_name_is_string_comparable(self) -> None:
        assert KpiName.LATENCY_MS == "latency_ms"


# ---------------------------------------------------------------------------
# KpiSample
# ---------------------------------------------------------------------------
class TestKpiSample:
    def test_construction(self) -> None:
        s = KpiSample(name=KpiName.LATENCY_MS, value=12.5, tick=10)
        assert s.name == KpiName.LATENCY_MS
        assert s.value == 12.5
        assert s.tick == 10

    def test_immutable(self) -> None:
        s = KpiSample(name=KpiName.LATENCY_MS, value=12.5, tick=10)
        with pytest.raises(ValidationError):
            s.value = 99.0  # type: ignore[misc]

    def test_tick_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            KpiSample(name=KpiName.LATENCY_MS, value=1.0, tick=-1)

    def test_str_representation(self) -> None:
        s = KpiSample(name=KpiName.LATENCY_MS, value=18.5, tick=5)
        assert "latency_ms" in str(s)
        assert "18.5" in str(s)
        assert "tick=5" in str(s)


# ---------------------------------------------------------------------------
# KpiSet — construction
# ---------------------------------------------------------------------------
class TestKpiSetConstruction:
    def test_defaults(self) -> None:
        k = KpiSet(name=KpiName.LATENCY_MS)
        assert k.current == 0.0
        assert k.smoothed == 0.0
        assert k.breaching is False
        assert k.alpha == 0.2

    def test_factory_for_latency(self) -> None:
        k = KpiSet.for_latency(high_ms=20.0, low_ms=15.0)
        assert k.high_threshold == 20.0
        assert k.low_threshold == 15.0
        assert k.floor == 0.0

    def test_factory_for_utilization(self) -> None:
        k = KpiSet.for_utilization(KpiName.PRB_UTILIZATION, high=0.85, low=0.70)
        assert k.ceil == 1.0
        assert k.floor == 0.0

    def test_invalid_thresholds_raise(self) -> None:
        """low_threshold must be strictly less than high_threshold."""
        with pytest.raises(ValidationError):
            KpiSet(
                name=KpiName.LATENCY_MS,
                high_threshold=10.0,
                low_threshold=10.0,  # equal → invalid
            )

    def test_low_greater_than_high_raises(self) -> None:
        with pytest.raises(ValidationError):
            KpiSet(
                name=KpiName.LATENCY_MS,
                high_threshold=10.0,
                low_threshold=15.0,  # reversed → invalid
            )


# ---------------------------------------------------------------------------
# KpiSet — update returns a new object (functional / immutable style)
# ---------------------------------------------------------------------------
class TestKpiSetUpdate:
    def test_update_returns_new_object(self) -> None:
        k = KpiSet(name=KpiName.LATENCY_MS)
        k2 = k.update(10.0)
        assert k is not k2

    def test_original_unchanged_after_update(self) -> None:
        k = KpiSet(name=KpiName.LATENCY_MS)
        k.update(99.0)
        assert k.current == 0.0   # original untouched

    def test_current_value_updated(self) -> None:
        k = KpiSet(name=KpiName.LATENCY_MS)
        k2 = k.update(18.0)
        assert k2.current == 18.0

    def test_max_tracked(self) -> None:
        k = KpiSet(name=KpiName.LATENCY_MS)
        k = k.update(10.0)
        k = k.update(25.0)
        k = k.update(5.0)
        assert k.maximum == 25.0

    def test_min_tracked(self) -> None:
        k = KpiSet(name=KpiName.LATENCY_MS)
        k = k.update(10.0)
        k = k.update(3.0)
        k = k.update(8.0)
        assert k.minimum == 3.0


# ---------------------------------------------------------------------------
# KpiSet — physical bounds clamping
# ---------------------------------------------------------------------------
class TestKpiSetClamping:
    def test_value_clamped_to_floor(self) -> None:
        k = KpiSet.for_latency()
        k2 = k.update(-5.0)   # below floor=0
        assert k2.current == 0.0

    def test_value_clamped_to_ceil(self) -> None:
        k = KpiSet.for_utilization(KpiName.PRB_UTILIZATION)
        k2 = k.update(1.5)    # above ceil=1
        assert k2.current == 1.0

    def test_value_within_bounds_unchanged(self) -> None:
        k = KpiSet.for_utilization(KpiName.COMPUTE_LOAD)
        k2 = k.update(0.6)
        assert k2.current == 0.6


# ---------------------------------------------------------------------------
# KpiSet — EMA smoothing
# ---------------------------------------------------------------------------
class TestKpiSetEMA:
    def test_ema_first_update(self) -> None:
        """First update: smoothed = alpha * value + (1-alpha) * 0."""
        k = KpiSet(name=KpiName.LATENCY_MS, alpha=0.2)
        k2 = k.update(10.0)
        expected = 0.2 * 10.0 + 0.8 * 0.0   # = 2.0
        assert abs(k2.smoothed - expected) < 1e-9

    def test_ema_converges_toward_stable_value(self) -> None:
        """After many updates with the same value, smoothed approaches that value."""
        k = KpiSet(name=KpiName.LATENCY_MS, alpha=0.3)
        for _ in range(50):
            k = k.update(20.0)
        assert abs(k.smoothed - 20.0) < 0.01


# ---------------------------------------------------------------------------
# KpiSet — hysteresis breach logic (the critical test group)
# (06-digital-twin.md §8: "breach on high, clear on low — no flapping")
# ---------------------------------------------------------------------------
class TestKpiSetHysteresis:
    def _latency_kpi(self) -> KpiSet:
        return KpiSet.for_latency(high_ms=20.0, low_ms=15.0)

    # --- Breach fires ---
    def test_breach_fires_when_above_high(self) -> None:
        k = self._latency_kpi()
        k2 = k.update(21.0)
        assert k2.breaching is True

    def test_no_breach_when_exactly_at_high(self) -> None:
        """Breach fires only when strictly ABOVE high_threshold."""
        k = self._latency_kpi()
        k2 = k.update(20.0)
        assert k2.breaching is False

    def test_no_breach_when_below_high(self) -> None:
        k = self._latency_kpi()
        k2 = k.update(19.9)
        assert k2.breaching is False

    # --- Clear fires ---
    def test_breach_clears_when_below_low(self) -> None:
        k = self._latency_kpi()
        k = k.update(21.0)   # trigger breach
        assert k.breaching is True
        k = k.update(14.9)   # below low_threshold=15 → clear
        assert k.breaching is False

    def test_breach_does_not_clear_between_thresholds(self) -> None:
        """Once breaching, stays breaching while value is between low and high."""
        k = self._latency_kpi()
        k = k.update(21.0)   # breach
        k = k.update(17.0)   # between 15 and 20 → still breaching
        assert k.breaching is True

    def test_breach_does_not_clear_exactly_at_low(self) -> None:
        """Clears only when strictly BELOW low_threshold."""
        k = self._latency_kpi()
        k = k.update(21.0)
        k = k.update(15.0)   # exactly at low → still breaching
        assert k.breaching is True

    # --- No flapping ---
    def test_no_flapping_oscillating_around_high(self) -> None:
        """
        A value oscillating just above and below the high threshold must NOT
        repeatedly flip breach on/off — that would be a flapping event storm.
        Once breached, it stays breached until it drops below LOW.
        """
        k = self._latency_kpi()
        # Oscillate around 20 (the high threshold)
        k = k.update(21.0)   # breach fires
        k = k.update(19.0)   # back below high — but STILL between thresholds
        k = k.update(21.0)   # above high again — still breaching (no re-fire)
        k = k.update(19.0)
        # Must still be breaching — never cleared because value never went below low=15
        assert k.breaching is True

    def test_full_cycle_breach_then_clear_then_breach_again(self) -> None:
        k = self._latency_kpi()
        # Cycle 1
        k = k.update(21.0)
        assert k.breaching is True
        k = k.update(10.0)   # drops well below low=15
        assert k.breaching is False
        # Cycle 2
        k = k.update(25.0)
        assert k.breaching is True
        k = k.update(5.0)
        assert k.breaching is False
