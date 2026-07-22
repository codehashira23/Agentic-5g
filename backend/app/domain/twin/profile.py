"""
Domain: Network Function profile — enums and value objects.

Defines:
  - NFType   : the 13 simulated NF/entity types (07-network-core.md)
  - NFStatus : lifecycle states an NF can be in (06-digital-twin.md §11)
  - Region   : geographic deployment region
  - NFProfile: typed, immutable description of a registered NF (NRF payload)

Rules (Clean Architecture / 03-architecture.md §5):
  - Pure Python + Pydantic only. Zero framework imports.
  - Immutable value objects (frozen=True) — no in-place mutation.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# NFType — the 13 NF/entity types simulated in the Digital Twin
# (07-network-core.md §6, 01-system.md §7)
# ---------------------------------------------------------------------------
class NFType(str, Enum):
    """Identifies which 5G network function a node represents."""

    UE = "UE"          # User Equipment (end device)
    GNB = "gNB"        # Radio base station (Next Generation NodeB)
    AMF = "AMF"        # Access & Mobility Management Function
    SMF = "SMF"        # Session Management Function
    UPF = "UPF"        # User Plane Function (packet forwarding)
    NRF = "NRF"        # Network Repository Function (registry & discovery)
    UDM = "UDM"        # Unified Data Management
    PCF = "PCF"        # Policy Control Function
    NWDAF = "NWDAF"    # Network Data Analytics Function
    NEF = "NEF"        # Network Exposure Function (northbound API)
    DCF = "DCF"        # Data Collection Coordination Function
    AF = "AF"          # Application Function
    EDGE = "Edge"      # Edge compute node


# ---------------------------------------------------------------------------
# NFStatus — lifecycle states (06-digital-twin.md §11, Figure 11.1)
# ---------------------------------------------------------------------------
class NFStatus(str, Enum):
    """Represents the operational state of a network function."""

    ACTIVE = "ACTIVE"           # healthy, serving requests
    DEGRADED = "DEGRADED"       # running but KPIs beyond warning threshold
    FAILED = "FAILED"           # not serving — fault injected or hazard triggered
    RECOVERING = "RECOVERING"   # transitioning back to ACTIVE
    STANDBY = "STANDBY"         # ready to be promoted (e.g. standby NRF)


# ---------------------------------------------------------------------------
# Region — geographic deployment region
# ---------------------------------------------------------------------------
class Region(str, Enum):
    """Logical deployment region for topology grouping and policy scoping."""

    DELHI = "Delhi"
    MUMBAI = "Mumbai"
    BENGALURU = "Bengaluru"
    CORE = "Core"       # central/non-regional (e.g. NRF, UDM)


# ---------------------------------------------------------------------------
# NFProfile — immutable value object used for NRF registration/discovery
# (07-network-core.md §4, 08-services.md §10.1)
# ---------------------------------------------------------------------------
class NFProfile(BaseModel):
    """
    The identity and capability description of a Network Function.

    Sent to the NRF on startup; returned by nrf.discover.
    Immutable — create a new profile instead of mutating.
    """

    model_config = {"frozen": True}  # immutable value object

    id: str = Field(
        ...,
        description="Unique NF instance id, e.g. 'upf_delhi_1'",
        examples=["upf_delhi_1", "nrf_core_1", "edge_delhi_1"],
    )
    type: NFType = Field(..., description="Which 5G NF this instance represents")
    region: Region = Field(..., description="Deployment region")
    status: NFStatus = Field(
        default=NFStatus.ACTIVE,
        description="Current operational status",
    )
    services: tuple[str, ...] = Field(
        default=(),
        description="Service names this NF produces, e.g. ('nrf.discover', 'nrf.register')",
    )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def is_healthy(self) -> bool:
        """Return True when the NF can serve requests."""
        return self.status in (NFStatus.ACTIVE, NFStatus.STANDBY)

    def with_status(self, status: NFStatus) -> NFProfile:
        """Return a new NFProfile with an updated status (immutable update)."""
        return self.model_copy(update={"status": status})
