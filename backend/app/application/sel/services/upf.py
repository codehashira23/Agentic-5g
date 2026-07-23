"""UPF user-plane services."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

UPF_SERVICES = [
    ServiceDescriptor(
        name="upf.loadbalance.apply", kind=ServiceKind.ACTION, owner_nf="UPF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:userplane", "region-scoped"),
        idempotent=False, compensation="upf.loadbalance.restore",
        spec_ref="TS 23.501 §6.2.3", approximates_operation="N4 session redistribution",
        description="Shift a fraction of sessions off this UPF. Guarded by PLC-4 (region) and PLC-6 (no-op if stable).",
    ),
    ServiceDescriptor(
        name="upf.loadbalance.restore", kind=ServiceKind.ACTION, owner_nf="UPF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:userplane",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.501 §6.2.3", approximates_operation="N4 session redistribution",
        description="Restore sessions moved by a prior loadbalance.apply (compensation service).",
    ),
    ServiceDescriptor(
        name="upf.session.install", kind=ServiceKind.ACTION, owner_nf="UPF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:userplane",),
        idempotent=True, compensation="upf.session.remove",
        spec_ref="TS 23.501 §6.2.3", approximates_operation="N4 session install",
        description="Install a PDU session on this UPF.",
    ),
    ServiceDescriptor(
        name="upf.session.remove", kind=ServiceKind.ACTION, owner_nf="UPF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:userplane",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.501 §6.2.3", approximates_operation="N4 session remove",
        description="Remove a PDU session from this UPF.",
    ),
    ServiceDescriptor(
        name="upf.metrics.get", kind=ServiceKind.READ, owner_nf="UPF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.3", approximates_operation="user-plane metrics",
        description="Return current UPF KPIs (latency, throughput, packet_loss, load).",
    ),
]
