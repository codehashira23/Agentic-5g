"""
C042: Unit tests for EventType, DomainEvent, and all specific event classes.
Verifies: enum completeness, envelope structure, immutability,
          default field values, and every concrete event type.
"""
from datetime import UTC

import pytest
from app.domain.twin.events import (
    DataCollectedEvent,
    EventType,
    KpiThresholdBreachEvent,
    KpiThresholdClearedEvent,
    KpiUpdatedEvent,
    ModelDeployedEvent,
    ModelRetiredEvent,
    NfDeregisteredEvent,
    NfFailedEvent,
    NfRecoveredEvent,
    NfRegisteredEvent,
    PolicyBlockedEvent,
    ServiceCalledEvent,
    ServiceResultEvent,
    SessionCreatedEvent,
    SessionReleasedEvent,
    SimTickEvent,
    UeAttachedEvent,
    UeHandoverEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowStageChangedEvent,
)
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# EventType enum
# ---------------------------------------------------------------------------
class TestEventType:
    def test_all_21_event_types_exist(self) -> None:
        expected = {
            "SIM_TICK",
            "KPI_UPDATED", "KPI_THRESHOLD_BREACH", "KPI_THRESHOLD_CLEARED",
            "NF_REGISTERED", "NF_DEREGISTERED", "NF_FAILED", "NF_RECOVERED",
            "UE_ATTACHED", "UE_HANDOVER", "SESSION_CREATED", "SESSION_RELEASED",
            "MODEL_DEPLOYED", "MODEL_RETIRED",
            "DATA_COLLECTED",
            "SERVICE_CALLED", "SERVICE_RESULT", "POLICY_BLOCKED",
            "WORKFLOW_STAGE_CHANGED", "WORKFLOW_COMPLETED", "WORKFLOW_FAILED",
        }
        assert {e.value for e in EventType} == expected

    def test_type_is_string_comparable(self) -> None:
        assert EventType.NF_FAILED == "NF_FAILED"
        assert EventType.KPI_THRESHOLD_BREACH == "KPI_THRESHOLD_BREACH"


# ---------------------------------------------------------------------------
# DomainEvent — base envelope
# ---------------------------------------------------------------------------
class TestDomainEvent:
    """Use a minimal concrete subclass to test the base."""

    def _make(self, **kwargs: object) -> SimTickEvent:
        return SimTickEvent(**kwargs)  # type: ignore[arg-type]

    def test_event_id_auto_generated(self) -> None:
        e = self._make()
        assert e.event_id is not None
        assert len(e.event_id) > 0

    def test_two_events_have_different_ids(self) -> None:
        e1 = self._make()
        e2 = self._make()
        assert e1.event_id != e2.event_id

    def test_ts_is_utc(self) -> None:
        e = self._make()
        assert e.ts.tzinfo is not None
        assert e.ts.tzinfo == UTC

    def test_default_tick_is_zero(self) -> None:
        e = self._make()
        assert e.tick == 0

    def test_tick_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            SimTickEvent(tick=-1)

    def test_correlation_id_defaults_to_none(self) -> None:
        e = self._make()
        assert e.correlation_id is None

    def test_correlation_id_can_be_set(self) -> None:
        e = SimTickEvent(correlation_id="wf_abc123", tick=5)
        assert e.correlation_id == "wf_abc123"

    def test_event_is_immutable(self) -> None:
        e = self._make()
        with pytest.raises(ValidationError):
            e.tick = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DomainEvent — to_envelope()
# ---------------------------------------------------------------------------
class TestDomainEventEnvelope:
    def test_envelope_has_required_keys(self) -> None:
        e = NfFailedEvent(entity_id="nrf_core_1", nf_type="NRF", tick=10)
        env = e.to_envelope()
        assert set(env.keys()) == {"type", "event_id", "correlation_id", "ts", "tick", "payload"}

    def test_envelope_type_is_string(self) -> None:
        e = NfFailedEvent(entity_id="nrf_core_1", nf_type="NRF")
        assert e.to_envelope()["type"] == "NF_FAILED"

    def test_envelope_ts_is_iso_string(self) -> None:
        e = SimTickEvent(tick=1)
        ts = e.to_envelope()["ts"]
        assert isinstance(ts, str)
        assert "T" in ts   # ISO 8601

    def test_envelope_payload_contains_extra_fields(self) -> None:
        e = NfFailedEvent(entity_id="upf_delhi_1", nf_type="UPF", cause="injected", tick=5)
        payload = e.to_envelope()["payload"]
        assert payload["entity_id"] == "upf_delhi_1"
        assert payload["nf_type"] == "UPF"
        assert payload["cause"] == "injected"

    def test_envelope_payload_excludes_base_fields(self) -> None:
        """Base fields (type, event_id, correlation_id, ts, tick) must not be in payload."""
        e = NfFailedEvent(entity_id="upf_1", nf_type="UPF")
        payload = e.to_envelope()["payload"]
        for base_field in ("type", "event_id", "correlation_id", "ts", "tick"):
            assert base_field not in payload


# ---------------------------------------------------------------------------
# Concrete event types — one construction test per class
# ---------------------------------------------------------------------------
class TestConcreteEvents:
    def test_sim_tick(self) -> None:
        e = SimTickEvent(tick=42)
        assert e.type == EventType.SIM_TICK
        assert e.tick == 42

    def test_kpi_updated(self) -> None:
        e = KpiUpdatedEvent(entity_id="upf_1", kpi="latency_ms", value=18.4, tick=1)
        assert e.type == EventType.KPI_UPDATED
        assert e.value == 18.4

    def test_kpi_threshold_breach(self) -> None:
        e = KpiThresholdBreachEvent(
            entity_id="upf_mumbai_1",
            kpi="latency_ms",
            value=21.0,
            threshold=20.0,
            region="Mumbai",
            tick=30,
            correlation_id="wf_abc",
        )
        assert e.type == EventType.KPI_THRESHOLD_BREACH
        assert e.value > e.threshold
        assert e.correlation_id == "wf_abc"

    def test_kpi_threshold_cleared(self) -> None:
        e = KpiThresholdClearedEvent(
            entity_id="upf_mumbai_1", kpi="latency_ms", value=12.0, region="Mumbai"
        )
        assert e.type == EventType.KPI_THRESHOLD_CLEARED

    def test_nf_registered(self) -> None:
        e = NfRegisteredEvent(entity_id="amf_core_1", nf_type="AMF")
        assert e.type == EventType.NF_REGISTERED

    def test_nf_deregistered(self) -> None:
        e = NfDeregisteredEvent(entity_id="amf_core_1", nf_type="AMF")
        assert e.type == EventType.NF_DEREGISTERED

    def test_nf_failed_default_cause(self) -> None:
        e = NfFailedEvent(entity_id="nrf_core_1", nf_type="NRF")
        assert e.type == EventType.NF_FAILED
        assert e.cause == "unknown"

    def test_nf_failed_custom_cause(self) -> None:
        e = NfFailedEvent(entity_id="nrf_core_1", nf_type="NRF", cause="injected")
        assert e.cause == "injected"

    def test_nf_recovered(self) -> None:
        e = NfRecoveredEvent(entity_id="nrf_core_1", nf_type="NRF")
        assert e.type == EventType.NF_RECOVERED

    def test_ue_attached(self) -> None:
        e = UeAttachedEvent(ue_id="ue_001", gnb_id="gnb_delhi_1", region="Delhi")
        assert e.type == EventType.UE_ATTACHED

    def test_ue_handover(self) -> None:
        e = UeHandoverEvent(
            ue_id="ue_001", from_gnb="gnb_delhi_1", to_gnb="gnb_delhi_2", region="Delhi"
        )
        assert e.type == EventType.UE_HANDOVER

    def test_session_created(self) -> None:
        e = SessionCreatedEvent(
            session_id="sess_1", ue_id="ue_001", smf_id="smf_core_1", upf_id="upf_delhi_1"
        )
        assert e.type == EventType.SESSION_CREATED

    def test_session_released(self) -> None:
        e = SessionReleasedEvent(session_id="sess_1", ue_id="ue_001")
        assert e.type == EventType.SESSION_RELEASED

    def test_model_deployed(self) -> None:
        e = ModelDeployedEvent(
            model_id="model_abc",
            model_name="congestion-det",
            target_id="edge_delhi_1",
            region="Delhi",
            correlation_id="wf_1a2b3c",
        )
        assert e.type == EventType.MODEL_DEPLOYED
        assert e.correlation_id == "wf_1a2b3c"

    def test_model_retired(self) -> None:
        e = ModelRetiredEvent(model_id="model_abc", target_id="edge_delhi_1")
        assert e.type == EventType.MODEL_RETIRED

    def test_data_collected(self) -> None:
        e = DataCollectedEvent(
            subscription_id="sub_001",
            producer_ids=("upf_delhi_1", "gnb_delhi_1"),
            sample_count=2,
        )
        assert e.type == EventType.DATA_COLLECTED
        assert e.sample_count == 2

    def test_service_called(self) -> None:
        e = ServiceCalledEvent(
            service_name="aimle.model.deploy",
            caller="executor",
            correlation_id="wf_xyz",
        )
        assert e.type == EventType.SERVICE_CALLED

    def test_service_result(self) -> None:
        e = ServiceResultEvent(
            service_name="aimle.model.deploy",
            status="ok",
            latency_ms=12.3,
            correlation_id="wf_xyz",
        )
        assert e.type == EventType.SERVICE_RESULT
        assert e.status == "ok"

    def test_policy_blocked(self) -> None:
        e = PolicyBlockedEvent(
            service_name="nrf.deregister",
            policy_id="PLC-1",
            message="Would leave zero active NRF",
            correlation_id="wf_xyz",
        )
        assert e.type == EventType.POLICY_BLOCKED
        assert "NRF" in e.message

    def test_workflow_stage_changed(self) -> None:
        e = WorkflowStageChangedEvent(
            workflow_id="wf_1a2b3c",
            from_stage="plan",
            to_stage="execute",
            status="running",
            correlation_id="wf_1a2b3c",
        )
        assert e.type == EventType.WORKFLOW_STAGE_CHANGED

    def test_workflow_completed(self) -> None:
        e = WorkflowCompletedEvent(
            workflow_id="wf_1a2b3c",
            goal="Deploy congestion model to Delhi Edge",
            correlation_id="wf_1a2b3c",
        )
        assert e.type == EventType.WORKFLOW_COMPLETED

    def test_workflow_failed(self) -> None:
        e = WorkflowFailedEvent(
            workflow_id="wf_1a2b3c",
            error="NRF unreachable",
            correlation_id="wf_1a2b3c",
        )
        assert e.type == EventType.WORKFLOW_FAILED
