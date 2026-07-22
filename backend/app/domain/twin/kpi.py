"""
Domain: KPI (Key Performance Indicator) value objects.

Defines:
  - KpiName   : the named KPIs tracked in the Digital Twin (06-digital-twin.md §8)
  - KpiSample : one timestamped reading of a KPI (immutable)
  - KpiSet    : the live KPI state for one NF — current value, EMA, thresholds,
                and hysteresis-based breach detection

Rules:
  - Pure Python + Pydantic only. Zero framework imports.
  - KpiSample is an immutable value object (frozen=True).
  - KpiSet uses hysteresis: breach fires when value > high_threshold,
    clears only when value < low_threshold — prevents event storms.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# KpiName — the named KPIs tracked in the Digital Twin
# (06-digital-twin.md §8, Table "Core KPIs per entity type")
# ---------------------------------------------------------------------------
class KpiName(str, Enum):
    """Standard KPI names used across all NF types."""

    LATENCY_MS = "latency_ms"                   # end-to-end user-plane latency
    THROUGHPUT_MBPS = "throughput_mbps"          # data throughput
    PRB_UTILIZATION = "prb_utilization"          # radio resource block utilisation (0-1)
    PACKET_LOSS = "packet_loss"                  # fraction of packets lost (0-1)
    REGISTRATION_LOAD = "registration_load"      # AMF: UE registrations/sec
    SESSION_SETUP_RATE = "session_setup_rate"    # SMF: sessions created/sec
    DISCOVERY_RATE = "discovery_rate"            # NRF: discovery requests/sec
    ANALYTICS_ACCURACY = "analytics_accuracy"    # NWDAF: model accuracy (0-1)
    COMPUTE_LOAD = "compute_load"                # Edge: compute utilisation (0-1)
    ENERGY_INDEX = "energy_index"                # relative energy consumption


# ---------------------------------------------------------------------------
# KpiSample — one timestamped reading (immutable)
# ---------------------------------------------------------------------------
class KpiSample(BaseModel):
    """A single, immutable KPI measurement at a point in time."""

    model_config = {"frozen": True}

    name: KpiName
    value: float
    tick: int = Field(..., ge=0, description="Simulation tick when this sample was taken")
    ts: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Wall-clock timestamp (UTC)",
    )

    def __str__(self) -> str:
        return f"{self.name.value}={self.value:.4f} @tick={self.tick}"


# ---------------------------------------------------------------------------
# KpiSet — live KPI state for one NF with hysteresis breach detection
# (06-digital-twin.md §8 — "Threshold hysteresis: breach when above high,
#  clear when below low — prevents event storms")
# ---------------------------------------------------------------------------
class KpiSet(BaseModel):
    """
    Tracks the current and smoothed value of one KPI for one NF, plus
    threshold configuration and hysteresis state.

    Hysteresis logic:
      - A breach is raised  when: current > high_threshold  AND not already breaching
      - A breach is cleared when: current < low_threshold   AND currently breaching

    This prevents the "event storm" where a KPI hovering near the threshold
    fires dozens of breach/clear events per second.
    """

    name: KpiName
    current: float = 0.0
    smoothed: float = 0.0          # exponential moving average (EMA)
    minimum: float = 0.0
    maximum: float = 0.0

    # Threshold configuration (high > low always)
    high_threshold: float = Field(default=float("inf"))
    low_threshold: float = Field(default=float("-inf"))

    # Physical bounds — values are clamped to [floor, ceil] after each update
    floor: float = Field(default=float("-inf"))
    ceil: float = Field(default=float("inf"))

    # Hysteresis state — True while a breach is active
    breaching: bool = False

    # EMA smoothing factor (0 < alpha ≤ 1)
    # Lower = more smoothing, slower response; higher = less smoothing, faster response
    alpha: float = Field(default=0.2, gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_thresholds(self) -> KpiSet:
        if self.high_threshold != float("inf") and self.low_threshold != float("-inf"):
            if self.low_threshold >= self.high_threshold:
                raise ValueError(
                    f"low_threshold ({self.low_threshold}) must be "
                    f"< high_threshold ({self.high_threshold})"
                )
        return self

    # ------------------------------------------------------------------
    # update — advance the KPI with a new reading
    # ------------------------------------------------------------------
    def update(self, new_value: float) -> KpiSet:
        """
        Return a NEW KpiSet with the updated value, EMA, min/max, and
        hysteresis state. Never mutates self (functional update).

        Returns the new KpiSet. Callers check .breaching to detect events:
            old = kpi_set
            new = kpi_set.update(reading)
            if not old.breaching and new.breaching:
                emit KPI_THRESHOLD_BREACH
            if old.breaching and not new.breaching:
                emit KPI_THRESHOLD_CLEARED
        """
        # 1. Clamp to physical bounds
        clamped = max(self.floor, min(self.ceil, new_value))

        # 2. Exponential moving average
        new_smoothed = self.alpha * clamped + (1.0 - self.alpha) * self.smoothed

        # 3. Min / max tracking
        new_min = min(self.minimum, clamped) if self.minimum != 0.0 else clamped
        new_max = max(self.maximum, clamped)

        # 4. Hysteresis breach detection
        new_breaching = self.breaching  # default: keep current state
        if not self.breaching and clamped > self.high_threshold:
            new_breaching = True   # trigger breach
        elif self.breaching and clamped < self.low_threshold:
            new_breaching = False  # clear breach

        return KpiSet(
            name=self.name,
            current=clamped,
            smoothed=new_smoothed,
            minimum=new_min,
            maximum=new_max,
            high_threshold=self.high_threshold,
            low_threshold=self.low_threshold,
            floor=self.floor,
            ceil=self.ceil,
            breaching=new_breaching,
            alpha=self.alpha,
        )

    # ------------------------------------------------------------------
    # Convenience factories
    # ------------------------------------------------------------------
    @classmethod
    def for_latency(
        cls,
        high_ms: float = 20.0,
        low_ms: float = 15.0,
    ) -> KpiSet:
        """Pre-configured KpiSet for latency (ms), floored at 0."""
        return cls(
            name=KpiName.LATENCY_MS,
            high_threshold=high_ms,
            low_threshold=low_ms,
            floor=0.0,
        )

    @classmethod
    def for_utilization(
        cls,
        name: KpiName,
        high: float = 0.85,
        low: float = 0.70,
    ) -> KpiSet:
        """Pre-configured KpiSet for 0-1 utilization metrics (PRB, compute, etc.)."""
        return cls(
            name=name,
            high_threshold=high,
            low_threshold=low,
            floor=0.0,
            ceil=1.0,
        )
