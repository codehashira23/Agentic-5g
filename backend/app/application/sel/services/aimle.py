"""AIMLE model lifecycle services."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

AIMLE_SERVICES = [
    ServiceDescriptor(
        name="aimle.model.deploy", kind=ServiceKind.ACTION, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:model", "region-scoped"),
        idempotent=False, compensation="aimle.model.retire",
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_MLModelProvision_Subscribe",
        description="Deploy an AI/ML model to a target NF or Edge node. Guarded by PLC-2 (healthy target).",
    ),
    ServiceDescriptor(
        name="aimle.model.retire", kind=ServiceKind.ACTION, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:model",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_MLModelProvision",
        description="Retire (remove) a deployed model from its target.",
    ),
    ServiceDescriptor(
        name="aimle.model.status", kind=ServiceKind.READ, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_MLModelProvision",
        description="Return the current state of a model instance.",
    ),
    ServiceDescriptor(
        name="aimle.model.register", kind=ServiceKind.ACTION, owner_nf="NWDAF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:model",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.288", approximates_operation="Nnwdaf_MLModelProvision",
        description="Register model metadata (name, version, metrics) without deploying.",
    ),
]
