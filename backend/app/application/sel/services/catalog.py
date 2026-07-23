"""
Aggregated service catalog — all services declared in one place.

Import this module to get the full list of ServiceDescriptors to register.
Owning docs: 08-services.md §10
"""
from __future__ import annotations

from app.domain.services.models import ServiceDescriptor

from .aimle import AIMLE_SERVICES
from .control_plane import AMF_SERVICES, NEF_SERVICES, PCF_SERVICES, SMF_SERVICES, UDM_SERVICES
from .dcf import DCF_SERVICES
from .edge import EDGE_SERVICES
from .nrf import NRF_SERVICES
from .nwdaf import NWDAF_SERVICES
from .twin_read import TWIN_READ_SERVICES
from .upf import UPF_SERVICES

ALL_SERVICES: list[ServiceDescriptor] = (
    NRF_SERVICES
    + TWIN_READ_SERVICES
    + NWDAF_SERVICES
    + DCF_SERVICES
    + AIMLE_SERVICES
    + UPF_SERVICES
    + EDGE_SERVICES
    + SMF_SERVICES
    + PCF_SERVICES
    + AMF_SERVICES
    + NEF_SERVICES
    + UDM_SERVICES
)


def get_catalog() -> list[ServiceDescriptor]:
    """Return the full service catalog."""
    return list(ALL_SERVICES)


def get_service_names() -> set[str]:
    return {s.name for s in ALL_SERVICES}
