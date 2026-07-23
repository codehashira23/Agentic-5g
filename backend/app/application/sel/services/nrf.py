"""NRF services — registration, discovery."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

NRF_SERVICES = [
    ServiceDescriptor(
        name="nrf.register", kind=ServiceKind.ACTION, owner_nf="NRF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:nrf",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.501 §6.2.6", approximates_operation="Nnrf_NFManagement_NFRegister",
        description="Register an NFProfile with the NRF.",
    ),
    ServiceDescriptor(
        name="nrf.deregister", kind=ServiceKind.ACTION, owner_nf="NRF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:nrf", "high-impact"),
        idempotent=True, compensation=None,
        spec_ref="TS 23.501 §6.2.6", approximates_operation="Nnrf_NFManagement_NFDeregister",
        description="Deregister an NFProfile. Guarded by PLC-1 (never zero NRF).",
    ),
    ServiceDescriptor(
        name="nrf.discover", kind=ServiceKind.READ, owner_nf="NRF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.6", approximates_operation="Nnrf_NFDiscovery_Request",
        description="Discover active NFs by type and/or region.",
    ),
    ServiceDescriptor(
        name="nrf.list", kind=ServiceKind.READ, owner_nf="NRF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.6", approximates_operation="Nnrf_NFManagement",
        description="List all registered NF profiles.",
    ),
]
