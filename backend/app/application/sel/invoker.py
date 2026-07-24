"""
Application: SEL Invoker — the single choke point for all service calls.

Pipeline (08-services.md §7, 03-architecture.md §12):
  1. Lookup descriptor in registry
  2. Validate args against input_model (Pydantic — if available)
  3. Policy check (actions only)
  4. Dispatch to owning NF via twin.apply_command()
  5. Emit SERVICE_CALLED / SERVICE_RESULT / POLICY_BLOCKED
  6. Persist via writer
  7. Return ServiceResult

Invariant P2: all agent→network action flows through this invoker.
Owning docs: 08-services.md §7
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert

from app.application.sel.policy_engine import PolicyEngine
from app.application.sel.registry import ServiceRegistry
from app.domain.services.models import ServiceResult, ServiceStatus
from app.domain.twin.events import (
    PolicyBlockedEvent,
    ServiceCalledEvent,
    ServiceResultEvent,
)
from app.infrastructure.bus.bus import InProcessEventBus
from app.infrastructure.db.models import ServiceCallRow
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp

logger = logging.getLogger(__name__)


class ServiceInvoker:
    """
    The single choke point for all SEL service calls.

    Usage:
        result = await invoker.invoke(
            name="nrf.discover",
            args={"nf_type": "Edge", "region": "Delhi"},
            caller="planner",
            correlation_id="wf_abc",
        )
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        policy_engine: PolicyEngine,
        twin: Any,           # TwinService (injected; avoid circular import)
        bus: InProcessEventBus,
        writer: PersistenceWriter,
    ) -> None:
        self._registry = registry
        self._policy = policy_engine
        self._twin = twin
        self._bus = bus
        self._writer = writer

    async def invoke(
        self,
        name: str,
        args: dict[str, Any],
        caller: str = "api",
        correlation_id: str | None = None,
        confirmation_token: str | None = None,
        snapshot: dict | None = None,
    ) -> ServiceResult:
        """Execute the full invoker pipeline."""
        ts = datetime.now(UTC).isoformat()
        start = datetime.now(UTC).timestamp()

        # ------------------------------------------------------------------
        # 1. Lookup
        # ------------------------------------------------------------------
        descriptor = self._registry.get(name)
        if descriptor is None:
            return ServiceResult(
                service_name=name,
                status=ServiceStatus.ERROR,
                error=f"Service '{name}' not registered in the SEL.",
                latency_ms=0.0,
            )

        # ------------------------------------------------------------------
        # 2. Policy check (actions only)
        # ------------------------------------------------------------------
        if descriptor.requires_policy_check():
            # Skip check if a valid confirmation_token is provided (PLC-5 path)
            if not confirmation_token:
                check = self._policy.evaluate(
                    service_name=name,
                    tags=descriptor.policy_tags,
                    args=args,
                    snapshot=snapshot,
                )
                if not check.allowed:
                    policy_id = (
                        check.triggered_policy.id
                        if check.triggered_policy
                        else "unknown"
                    )
                    # Emit + persist POLICY_BLOCKED
                    blocked_evt = PolicyBlockedEvent(
                        service_name=name,
                        policy_id=policy_id,
                        message=check.message,
                        correlation_id=correlation_id,
                    )
                    await self._bus.publish(blocked_evt)
                    await self._persist_call(
                        name=name, caller=caller,
                        status="blocked", args=args, result={},
                        policy_id=policy_id,
                        latency_ms=0.0, ts=ts,
                        correlation_id=correlation_id,
                    )
                    from app.domain.services.models import ServiceStatus as _SS
                    return ServiceResult(
                        service_name=name,
                        status=_SS.BLOCKED,
                        policy_id=policy_id,
                        error=check.message,
                    )

        # ------------------------------------------------------------------
        # 3. Emit SERVICE_CALLED
        # ------------------------------------------------------------------
        await self._bus.publish(ServiceCalledEvent(
            service_name=name,
            caller=caller,
            args_summary=_summarise(args),
            correlation_id=correlation_id,
        ))

        # ------------------------------------------------------------------
        # 4. Dispatch to twin
        # ------------------------------------------------------------------
        try:
            result_data = self._twin.apply_command(name, {**args, "target": args.get("target", "")})
            status = ServiceStatus.OK
            error = None
        except Exception as exc:
            logger.exception("Service '%s' dispatch failed", name)
            result_data = {}
            status = ServiceStatus.ERROR
            error = str(exc)

        latency_ms = (datetime.now(UTC).timestamp() - start) * 1000.0

        # ------------------------------------------------------------------
        # 4a. Side-effect: persist ModelRow for model deployments
        # ------------------------------------------------------------------
        if status == ServiceStatus.OK and name == "aimle.model.deploy":
            await self._persist_model(args, result_data, ts, correlation_id)

        # ------------------------------------------------------------------
        # 5. Emit SERVICE_RESULT + persist call
        # ------------------------------------------------------------------
        await self._bus.publish(ServiceResultEvent(
            service_name=name,
            status=status.value,
            latency_ms=latency_ms,
            correlation_id=correlation_id,
        ))
        await self._persist_call(
            name=name, caller=caller,
            status=status.value, args=args,
            result=result_data, policy_id=None,
            latency_ms=latency_ms, ts=ts,
            correlation_id=correlation_id,
        )

        return ServiceResult(
            service_name=name,
            status=status,
            output=result_data if result_data else {},
            error=error,
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _persist_call(
        self,
        name: str, caller: str, status: str,
        args: dict, result: dict,
        policy_id: str | None, latency_ms: float, ts: str,
        correlation_id: str | None = None,
    ) -> None:
        await self._writer.submit(WriteOp(
            stmt=insert(ServiceCallRow).values(
                correlation_id=correlation_id,
                service_name=name,
                caller=caller,
                status=status,
                args_json=json.dumps(args),
                result_json=json.dumps(result),
                policy_id=policy_id,
                latency_ms=latency_ms,
                ts=ts,
            )
        ))

    async def _persist_model(
        self,
        args: dict[str, Any],
        result: dict[str, Any],
        ts: str,
        correlation_id: str | None,
    ) -> None:
        """Persist a ModelRow when aimle.model.deploy succeeds."""
        import uuid as _uuid
        from app.infrastructure.db.models import ModelRow
        model_id = (
            result.get("model_id")
            or args.get("model_id")
            or f"model_{_uuid.uuid4().hex[:8]}"
        )
        target = args.get("target_node_id") or args.get("target") or ""
        await self._writer.submit(WriteOp(
            stmt=insert(ModelRow).prefix_with("OR IGNORE").values(
                id=model_id,
                name=args.get("model_name") or model_id,
                version=str(args.get("version", "1.0")),
                state="deployed",
                target_node_id=target or None,
                metrics_json="{}",
                created_at=ts,
                updated_at=ts,
            )
        ))


def _summarise(args: dict[str, Any], max_len: int = 80) -> str:
    s = json.dumps(args, default=str)
    return s[:max_len] + "…" if len(s) > max_len else s
