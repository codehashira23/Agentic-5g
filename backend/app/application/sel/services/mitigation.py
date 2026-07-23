"""
Mitigation services — the agent-invokable actions for Scenario B.
These are the services the Optimizer proposes and the Executor applies
to recover from a congestion breach.
"""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

MITIGATION_SERVICES = [
    # Already in upf.py but explicit compensation here for clarity
    ServiceDescriptor(
        name="upf.loadbalance.restore",
        kind=ServiceKind.ACTION,
        owner_nf="UPF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:userplane",),
        idempotent=True,
        compensation=None,
        spec_ref="TS 23.501 §6.2.3",
        approximates_operation="N4 session redistribution",
        description="Restore sessions after a loadbalance.apply (compensation).",
    ),
]
