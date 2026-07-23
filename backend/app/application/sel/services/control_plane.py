"""SMF, PCF, AMF, UDM, NEF, AF service descriptors."""
from app.domain.services.models import Pattern, ServiceDescriptor, ServiceKind

SMF_SERVICES = [
    ServiceDescriptor(
        name="smf.session.create", kind=ServiceKind.ACTION, owner_nf="SMF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:session",),
        idempotent=False, compensation="smf.session.release",
        spec_ref="TS 23.501 §6.2.2", approximates_operation="Nsmf_PDUSession_CreateSMContext",
        description="Establish a PDU session.",
    ),
    ServiceDescriptor(
        name="smf.session.modify", kind=ServiceKind.ACTION, owner_nf="SMF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:session",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.501 §6.2.2", approximates_operation="Nsmf_PDUSession_UpdateSMContext",
        description="Modify QoS on an existing PDU session.",
    ),
    ServiceDescriptor(
        name="smf.session.release", kind=ServiceKind.ACTION, owner_nf="SMF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:session",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.501 §6.2.2", approximates_operation="Nsmf_PDUSession_ReleaseSMContext",
        description="Release a PDU session.",
    ),
    ServiceDescriptor(
        name="smf.session.list", kind=ServiceKind.READ, owner_nf="SMF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.2", approximates_operation="Nsmf_PDUSession",
        description="List active sessions for a UE.",
    ),
]

PCF_SERVICES = [
    ServiceDescriptor(
        name="pcf.policy.apply", kind=ServiceKind.ACTION, owner_nf="PCF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:policy",),
        idempotent=False, compensation=None,
        spec_ref="TS 23.501 §6.2.4", approximates_operation="Npcf_SMPolicyControl_Update",
        description="Apply a QoS/prioritisation policy rule.",
    ),
    ServiceDescriptor(
        name="pcf.policy.get", kind=ServiceKind.READ, owner_nf="PCF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.4", approximates_operation="Npcf_SMPolicyControl",
        description="Return active policy rules for a scope.",
    ),
    ServiceDescriptor(
        name="pcf.policy.list", kind=ServiceKind.READ, owner_nf="PCF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.4", approximates_operation="Npcf_SMPolicyControl",
        description="List all policy rule ids.",
    ),
]

AMF_SERVICES = [
    ServiceDescriptor(
        name="amf.ue.register", kind=ServiceKind.ACTION, owner_nf="AMF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:registration",),
        idempotent=True, compensation="amf.ue.deregister",
        spec_ref="TS 23.501 §6.2.1", approximates_operation="Namf_Communication",
        description="Register a UE with the AMF.",
    ),
    ServiceDescriptor(
        name="amf.ue.deregister", kind=ServiceKind.ACTION, owner_nf="AMF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:registration",),
        idempotent=True, compensation=None,
        spec_ref="TS 23.501 §6.2.1", approximates_operation="Namf_Communication",
        description="Deregister a UE from the AMF.",
    ),
    ServiceDescriptor(
        name="amf.ue.context.get", kind=ServiceKind.READ, owner_nf="AMF",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.1", approximates_operation="Namf_Communication",
        description="Return a UE's registration context.",
    ),
]

NEF_SERVICES = [
    ServiceDescriptor(
        name="nef.qos.request", kind=ServiceKind.ACTION, owner_nf="NEF",
        pattern=Pattern.REQUEST_RESPONSE,
        policy_tags=("mutates:qos", "region-scoped"),
        idempotent=False, compensation=None,
        spec_ref="TS 23.501 §6.2.5", approximates_operation="Nnef_AFsessionWithQoS",
        description="Request QoS-on-Demand for a flow (CAMARA-style).",
    ),
    ServiceDescriptor(
        name="nef.event.subscribe", kind=ServiceKind.ACTION, owner_nf="NEF",
        pattern=Pattern.SUBSCRIBE_NOTIFY,
        policy_tags=(),
        idempotent=False, compensation=None,
        spec_ref="TS 23.501 §6.2.5", approximates_operation="Nnef_EventExposure_Subscribe",
        description="Subscribe to network events via NEF.",
    ),
]

UDM_SERVICES = [
    ServiceDescriptor(
        name="udm.subscriber.get", kind=ServiceKind.READ, owner_nf="UDM",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.7", approximates_operation="Nudm_SDM_Get",
        description="Return synthetic subscriber profile (no real PII).",
    ),
    ServiceDescriptor(
        name="udm.subscription.get", kind=ServiceKind.READ, owner_nf="UDM",
        pattern=Pattern.REQUEST_RESPONSE,
        spec_ref="TS 23.501 §6.2.7", approximates_operation="Nudm_UECM",
        description="Return subscription data for a UE.",
    ),
]
