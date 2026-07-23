"""NWDAF analytics services."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

NWDAF_SERVICES = [
    ServiceDescriptor(
        name="nwdaf.analytics.congestion.subscribe",
        kind=ServiceKind.ACTION, owner_nf="NWDAF",
        pattern=Pattern.SUBSCRIBE_NOTIFY,
        policy_tags=(),
        idempotent=False, compensation="nwdaf.analytics.unsubscribe",
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_AnalyticsSubscription_Subscribe",
        description="Subscribe to congestion analytics notifications for a region.",
    ),
    ServiceDescriptor(
        name="nwdaf.analytics.congestion.query",
        kind=ServiceKind.READ, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_AnalyticsInfo_Request",
        description="Query current congestion analytics for a region.",
    ),
    ServiceDescriptor(
        name="nwdaf.analytics.unsubscribe",
        kind=ServiceKind.ACTION, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=(),
        idempotent=True, compensation=None,
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_AnalyticsSubscription",
        description="Cancel a NWDAF analytics subscription.",
    ),
    ServiceDescriptor(
        name="nwdaf.analytics.qos.predict",
        kind=ServiceKind.READ, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_AnalyticsInfo_Request",
        description="Predict QoS degradation over a time horizon.",
    ),
    ServiceDescriptor(
        name="nwdaf.analytics.load.query",
        kind=ServiceKind.READ, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_AnalyticsInfo_Request",
        description="Query load analytics for an NF or region.",
    ),
    ServiceDescriptor(
        name="nwdaf.analytics.abnormal.subscribe",
        kind=ServiceKind.ACTION, owner_nf="NWDAF",
        pattern=Pattern.SUBSCRIBE_NOTIFY,
        policy_tags=(),
        idempotent=False, compensation="nwdaf.analytics.unsubscribe",
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_AnalyticsSubscription_Subscribe",
        description="Subscribe to abnormal-behaviour analytics.",
    ),
]
