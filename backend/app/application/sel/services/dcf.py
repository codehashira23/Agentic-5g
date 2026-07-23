"""DCF data collection services."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

DCF_SERVICES = [
    ServiceDescriptor(
        name="dcf.data.subscribe", kind=ServiceKind.ACTION, owner_nf="DCF",
        pattern=Pattern.SUBSCRIBE_NOTIFY,
        policy_tags=(),
        idempotent=False, compensation="dcf.data.unsubscribe",
        spec_ref="TS 23.288", approximates_operation="Ndccf_DataManagement_Subscribe",
        description="Subscribe to coordinated data collection from producers.",
    ),
    ServiceDescriptor(
        name="dcf.data.unsubscribe", kind=ServiceKind.ACTION, owner_nf="DCF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=(),
        idempotent=True, compensation=None,
        spec_ref="TS 23.288", approximates_operation="Ndccf_DataManagement",
        description="Cancel a DCF data collection subscription.",
    ),
    ServiceDescriptor(
        name="dcf.data.query", kind=ServiceKind.READ, owner_nf="DCF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.288", approximates_operation="Ndccf_DataManagement",
        description="Query the latest collected value for a metric.",
    ),
    ServiceDescriptor(
        name="dcf.data.history", kind=ServiceKind.READ, owner_nf="DCF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.288", approximates_operation="Nadrf_DataManagement_Retrieve",
        description="Return historical KPI samples (ADRF-like repo).",
    ),
]
