"""
Domain: NetworkFunction — the abstract base for every simulated NF/entity.

Defines:
  - RngStream      : minimal protocol the domain uses for randomness
                     (actual implementation lives in infrastructure/rng)
  - AdvanceContext : read-only context passed to advance() each tick
  - NetworkFunction: abstract base — all 13 NF types inherit from this

Rules (Clean Architecture):
  - Pure Python + Pydantic only. Zero framework imports.
  - advance() returns a list of DomainEvents; it never mutates shared state
    or calls external services.
  - handle() is the entry-point the SEL Invoker calls for service requests.
  - All randomness must come from ctx.rng — never random.random() directly
    (GR4 / TP2: determinism).

Owning docs: 06-digital-twin.md §4-§5, 07-network-core.md §6
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.domain.twin.events import DomainEvent
from app.domain.twin.kpi import KpiName, KpiSet
from app.domain.twin.profile import NFProfile, NFStatus, NFType, Region


# ---------------------------------------------------------------------------
# RngStream — minimal randomness protocol (dependency inversion)
# The real implementation is in infrastructure/rng/rng.py (C060).
# Tests inject a FakeRng; production injects the seeded RngService.
# ---------------------------------------------------------------------------
@runtime_checkable
class RngStream(Protocol):
    """Protocol: a source of random numbers for one simulation tick."""

    def random(self) -> float:
        """Return a float in [0.0, 1.0)."""
        ...

    def gauss(self, mu: float, sigma: float) -> float:
        """Return a Gaussian sample with the given mean and std-dev."""
        ...

    def uniform(self, lo: float, hi: float) -> float:
        """Return a uniform sample in [lo, hi)."""
        ...


# ---------------------------------------------------------------------------
# AdvanceContext — passed to every NF on each simulation tick
# ---------------------------------------------------------------------------
class AdvanceContext(BaseModel):
    """
    Read-only context provided to NetworkFunction.advance() on every tick.
    Keeps advance() a pure function of (self, rng, ctx) — testable in
    isolation without starting a server or database.
    """

    model_config = {"frozen": True}

    tick: int = Field(..., ge=0)
    demand_factor: float = Field(
        default=1.0,
        description="Regional traffic demand multiplier from the diurnal profile "
        "(06-digital-twin.md §9). 1.0 = baseline; >1.0 = busy hour.",
    )
    connected_nf_ids: frozenset[str] = Field(
        default_factory=frozenset,
        description="IDs of NFs this entity is directly connected to, "
        "so an NF can react to neighbour state changes.",
    )


# ---------------------------------------------------------------------------
# NetworkFunction — abstract base class
# (07-network-core.md §6: every NF subclass implements advance + handle)
# ---------------------------------------------------------------------------
class NetworkFunction(ABC):
    """
    Abstract base for every simulated 5G network function.

    Concrete subclasses (NRF, AMF, SMF, UPF, NWDAF …) override:
      - advance(rng, ctx) → list[DomainEvent]   : tick-driven state evolution
      - handle(service_name, args) → dict        : SEL service dispatch

    Public read-only surface:
      - profile      : the current NFProfile (id, type, region, status, services)
      - kpis         : dict[KpiName, KpiSet] — live KPI state
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(
        self,
        nf_id: str,
        nf_type: NFType,
        region: Region,
        services: tuple[str, ...] = (),
        status: NFStatus = NFStatus.ACTIVE,
        load: float = 0.0,
    ) -> None:
        self._profile = NFProfile(
            id=nf_id,
            type=nf_type,
            region=region,
            status=status,
            services=services,
        )
        self._load: float = max(0.0, min(1.0, load))   # clamped to [0, 1]
        self._kpis: dict[KpiName, KpiSet] = {}

    # ------------------------------------------------------------------
    # Public properties (read-only)
    # ------------------------------------------------------------------
    @property
    def profile(self) -> NFProfile:
        """Current NFProfile — the NRF registration payload."""
        return self._profile

    @property
    def id(self) -> str:
        return self._profile.id

    @property
    def nf_type(self) -> NFType:
        return self._profile.type

    @property
    def region(self) -> Region:
        return self._profile.region

    @property
    def status(self) -> NFStatus:
        return self._profile.status

    @property
    def load(self) -> float:
        """Current normalised load in [0, 1]."""
        return self._load

    @property
    def kpis(self) -> dict[KpiName, KpiSet]:
        """Live KPI state (read-only view)."""
        return dict(self._kpis)

    def is_healthy(self) -> bool:
        """True when this NF can serve requests (ACTIVE or STANDBY)."""
        return self._profile.is_healthy()

    # ------------------------------------------------------------------
    # Abstract interface — subclasses MUST implement these two methods
    # ------------------------------------------------------------------
    @abstractmethod
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        """
        Advance this NF by one simulation tick.

        Must:
          - Use rng for all randomness (GR4 / TP2 — determinism).
          - Return a list of DomainEvents (may be empty).
          - Never call external I/O.
          - Never raise; absorb errors and return an NfFailedEvent if needed.

        Args:
            rng : per-tick seeded random stream from infrastructure/rng
            ctx : read-only context (tick, demand_factor, neighbour ids)

        Returns:
            list of DomainEvents emitted this tick (can be []).
        """
        ...

    @abstractmethod
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Dispatch a SEL service call to this NF.

        Called by the SEL Invoker (application/sel/invoker.py) after
        policy-check passes.  Must return a plain dict that the invoker
        wraps into a ServiceResult.

        Args:
            service_name : the dotted service name, e.g. "nrf.discover"
            args         : validated input (Pydantic has already checked types)

        Returns:
            A plain dict that becomes the ServiceResult.output.

        Raises:
            ValueError  : if service_name is not produced by this NF.
            RuntimeError: for unexpected internal errors.
        """
        ...

    # ------------------------------------------------------------------
    # Protected helpers — available to all subclasses
    # ------------------------------------------------------------------
    def _set_status(self, status: NFStatus) -> None:
        """Update the NF status (replaces the immutable NFProfile)."""
        self._profile = self._profile.with_status(status)

    def _set_load(self, load: float) -> None:
        """Update normalised load, clamped to [0, 1]."""
        self._load = max(0.0, min(1.0, load))

    def _set_kpi(self, kpi_set: KpiSet) -> None:
        """Store an updated KpiSet."""
        self._kpis[kpi_set.name] = kpi_set

    def _get_kpi(self, name: KpiName) -> KpiSet:
        """Return the KpiSet for a KPI, or a default zero KpiSet."""
        return self._kpis.get(name, KpiSet(name=name))

    def _unsupported(self, service_name: str) -> ValueError:
        """Helper: raise a clear error for unknown service names."""
        return ValueError(
            f"{self._profile.type.value} '{self._profile.id}' "
            f"does not produce service '{service_name}'"
        )

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self._profile.id!r}, "
            f"status={self._profile.status.value!r}, "
            f"load={self._load:.2f})"
        )
