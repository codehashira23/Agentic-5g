"""Edge node services (AIMLE deployment target)."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

EDGE_SERVICES = [
    ServiceDescriptor(
        name="edge.model.host", kind=ServiceKind.ACTION, owner_nf="Edge",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:model", "region-scoped"),
        idempotent=False, compensation="aimle.model.retire",
        spec_ref="TS 23.548", approximates_operation="local model hosting",
        description="Host an AI/ML model on this edge node (alias for aimle.model.deploy).",
    ),
    ServiceDescriptor(
        name="edge.model.run", kind=ServiceKind.ACTION, owner_nf="Edge",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:edge",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.548", approximates_operation="local inference",
        description="Run inference on a hosted model at the edge.",
    ),
    ServiceDescriptor(
        name="edge.metrics.get", kind=ServiceKind.READ, owner_nf="Edge",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.548", approximates_operation="edge metrics",
        description="Return current edge KPIs (compute_load, latency_ms, hosted_model_count).",
    ),
]
