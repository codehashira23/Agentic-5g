"""
Domain: NRF — Network Repository Function.

Role (07-network-core.md §6.6):
  The NRF is the SBA registry — every NF registers here on startup and
  is discovered here by consumers.  It is the single point of discovery
  for the whole network.  If it fails, nothing can find anything.

Simulated state:
  - registry   : dict[nf_id → NFProfile]  — all registered NFs
  - request_rate: float                   — discovery calls / tick (KPI)

Produced services (registered in the SEL catalog, 08-services.md §10.1):
  nrf.register   — add an NFProfile to the registry
  nrf.deregister — remove an NFProfile
  nrf.discover   — query profiles by type / region
  nrf.list       — return all registered profiles

Domain invariant (GR8 / PLC-1 / 07-network-core.md §6.6):
  deregister() RAISES if it would leave ZERO active NRFs of the same type.
  This is the domain-level defence-in-depth; PLC-1 in the SEL is the
  application-level guard.  Both exist so safety is belt-and-braces.

Standards mapping:
  spec_ref              : TS 23.501 §6.2.6, TS 23.502 §5.2.7
  approximates_operation: Nnrf_NFManagement_NFRegister/Deregister,
                          Nnrf_NFDiscovery_Request

Rules:
  - Pure Python + Pydantic only. Zero framework imports.
  - All randomness through rng (GR4).
  - advance() returns DomainEvents; never raises.
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
from app.domain.twin.profile import NFProfile, NFStatus, NFType, Region

# Services this NF produces
_SERVICES: tuple[str, ...] = (
    "nrf.register",
    "nrf.deregister",
    "nrf.discover",
    "nrf.list",
)

# Failure hazard probability per tick (very low — NRF is critical)
_HAZARD_PROB: float = 0.001
# Auto-recovery probability per tick when FAILED
_RECOVERY_PROB: float = 0.05


class NRF(NetworkFunction):
    """
    Simulated Network Repository Function.

    The NRF is special: it is the discovery anchor for the whole SBA.
    Its failure (Scenario C) triggers the Recovery agent.
    """

    def __init__(
        self,
        nf_id: str = "nrf_core_1",
        region: Region = Region.CORE,
        status: NFStatus = NFStatus.ACTIVE,
        is_standby: bool = False,
    ) -> None:
        super().__init__(
            nf_id=nf_id,
            nf_type=NFType.NRF,
            region=region,
            services=_SERVICES,
            status=status,
        )
        # registry: maps nf_id → NFProfile
        self._registry: dict[str, NFProfile] = {}
        # total discovery requests served this tick (for KPI)
        self._request_rate: float = 0.0
        # standby NRFs can be promoted to ACTIVE by the Recovery agent
        self.is_standby: bool = is_standby

        # initialise KPIs
        self._set_kpi(KpiSet(name=KpiName.DISCOVERY_RATE))

    # ------------------------------------------------------------------
    # advance — tick-driven state evolution
    # ------------------------------------------------------------------
    def advance(self, rng: RngStream, ctx: AdvanceContext) -> list[DomainEvent]:
        """
        Each tick:
        1. If ACTIVE  → small chance of stochastic failure.
        2. If FAILED  → small chance of auto-recovery.
        3. Update discovery_rate KPI with noisy demand-scaled value.
        """
        events: list[DomainEvent] = []

        if self._profile.status == NFStatus.ACTIVE:
            # --- Stochastic failure ---
            if rng.random() < _HAZARD_PROB:
                self._set_status(NFStatus.FAILED)
                events.append(
                    NfFailedEvent(
                        entity_id=self.id,
                        nf_type=NFType.NRF.value,
                        cause="hazard",
                        tick=ctx.tick,
                    )
                )
                return events  # skip KPI update on failure tick

            # --- KPI: discovery_rate (demand-scaled + noise) ---
            base_rate = 10.0 * ctx.demand_factor
            noisy = base_rate + rng.gauss(0.0, 1.0)
            noisy = max(0.0, noisy)
            old_kpi = self._get_kpi(KpiName.DISCOVERY_RATE)
            new_kpi = old_kpi.update(noisy)
            self._set_kpi(new_kpi)
            self._request_rate = new_kpi.current

            events.append(
                KpiUpdatedEvent(
                    entity_id=self.id,
                    kpi=KpiName.DISCOVERY_RATE.value,
                    value=new_kpi.current,
                    tick=ctx.tick,
                )
            )

        elif self._profile.status == NFStatus.FAILED:
            # --- Auto-recovery ---
            if rng.random() < _RECOVERY_PROB:
                self._set_status(NFStatus.ACTIVE)
                events.append(
                    NfRecoveredEvent(
                        entity_id=self.id,
                        nf_type=NFType.NRF.value,
                        tick=ctx.tick,
                    )
                )

        return events

    # ------------------------------------------------------------------
    # handle — SEL service dispatch
    # ------------------------------------------------------------------
    def handle(self, service_name: str, args: dict[str, Any]) -> dict[str, Any]:
        match service_name:
            case "nrf.register":
                return self._handle_register(args)
            case "nrf.deregister":
                return self._handle_deregister(args)
            case "nrf.discover":
                return self._handle_discover(args)
            case "nrf.list":
                return self._handle_list(args)
            case _:
                raise self._unsupported(service_name)

    # ------------------------------------------------------------------
    # Service handlers
    # ------------------------------------------------------------------
    def _handle_register(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Register an NFProfile.  Idempotent — re-registering the same id
        replaces the old entry (profile update on restart).
        """
        profile = NFProfile(**args["profile"])
        self._registry[profile.id] = profile
        return {"registered": True, "nf_id": profile.id}

    def _handle_deregister(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Remove an NFProfile.

        Domain invariant (PLC-1 defence-in-depth):
        Refuses if this would leave ZERO active NRFs of the same type in
        the registry.
        """
        nf_id: str = args["nf_id"]

        if nf_id not in self._registry:
            return {"deregistered": False, "reason": f"'{nf_id}' not found"}

        target = self._registry[nf_id]
        # Count how many active NFs of this type remain after removal
        remaining_active = sum(
            1
            for p in self._registry.values()
            if p.type == target.type
            and p.id != nf_id
            and p.status == NFStatus.ACTIVE
        )

        if target.type == NFType.NRF and remaining_active == 0:
            raise ValueError(
                f"PLC-1 violation: deregistering '{nf_id}' would leave "
                f"zero active NRF instances. Refused."
            )

        del self._registry[nf_id]
        return {"deregistered": True, "nf_id": nf_id}

    def _handle_discover(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Return NFProfiles matching the given filters.

        args keys (all optional):
          nf_type  : str  — filter by NFType value
          region   : str  — filter by Region value
          status   : str  — filter by NFStatus (default: only ACTIVE)
        """
        self._request_rate += 1.0   # count each discovery call

        type_filter: str | None = args.get("nf_type")
        region_filter: str | None = args.get("region")
        status_filter: str = args.get("status", NFStatus.ACTIVE.value)

        results = [
            p
            for p in self._registry.values()
            if (type_filter is None or p.type.value == type_filter)
            and (region_filter is None or p.region.value == region_filter)
            and p.status.value == status_filter
        ]

        return {
            "profiles": [p.model_dump() for p in results],
            "count": len(results),
        }

    def _handle_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """Return all registered profiles regardless of status."""
        return {
            "profiles": [p.model_dump() for p in self._registry.values()],
            "count": len(self._registry),
        }

    # ------------------------------------------------------------------
    # Read-only helpers (used by tests and the twin snapshot)
    # ------------------------------------------------------------------
    @property
    def registry(self) -> dict[str, NFProfile]:
        """Read-only copy of the registry."""
        return dict(self._registry)

    @property
    def registered_count(self) -> int:
        return len(self._registry)

    def promote_standby(self) -> None:
        """
        Promote this NRF from STANDBY → ACTIVE.
        Called by the Recovery agent when the primary NRF fails (Scenario C).
        """
        if self.is_standby and self._profile.status == NFStatus.STANDBY:
            self._set_status(NFStatus.ACTIVE)
            self.is_standby = False
