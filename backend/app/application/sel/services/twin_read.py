"""Twin read services — side-effect-free snapshot and topology reads."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

TWIN_READ_SERVICES = [
    ServiceDescriptor(
        name="twin.snapshot", kind=ServiceKind.READ, owner_nf="NetworkTwin",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="internal", approximates_operation="twin aggregate snapshot",
        description="Return a full twin snapshot (all NF states + KPIs).",
    ),
    ServiceDescriptor(
        name="topology.get", kind=ServiceKind.READ, owner_nf="NetworkTwin",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="internal", approximates_operation="topology graph read",
        description="Return the topology graph (nodes + links), optionally filtered by region.",
    ),
]
