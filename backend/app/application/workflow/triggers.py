"""
Autonomous Observer triggering — the closed loop.

The Observer subscribes to KPI_THRESHOLD_BREACH and NF_FAILED events.
When one fires (and autonomy is enabled + no workflow is already handling
the same condition), a new workflow is started with no human prompt.

De-duplication registry:
  Key: (event_type, entity_id, region)
  Value: workflow_id that is handling it
  Cleared when the workflow completes/fails.

Owning docs: 13-workflow-engine.md §12
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AutoTrigger:
    """
    Observer autonomous trigger with de-duplication.

    Usage (in the lifespan after bus + engine are ready):
        trigger = AutoTrigger(bus, engine, autonomy_enabled=True)
        trigger.subscribe()
    """

    def __init__(
        self,
        bus: Any,
        engine: Any,
        autonomy_enabled: bool = True,
    ) -> None:
        self._bus = bus
        self._engine = engine
        self._autonomy_enabled = autonomy_enabled
        # in-flight: key → workflow_id being handled
        self._in_flight: dict[str, str] = {}
        self._subscription: Any = None

    def subscribe(self) -> None:
        """Register handlers for breach and failure events."""
        self._subscription = self._bus.subscribe(
            event_types=["KPI_THRESHOLD_BREACH", "NF_FAILED"],
            handler=self._handle_event,
            lossless=True,
        )
        logger.info("AutoTrigger subscribed to breach/failure events")

    async def _handle_event(self, event: Any) -> None:
        if not self._autonomy_enabled:
            return

        evt_type: str = getattr(event, "type", "")
        if hasattr(evt_type, "value"):
            evt_type = evt_type.value

        entity_id: str = getattr(event, "entity_id", "")
        region: str = ""

        if evt_type == "KPI_THRESHOLD_BREACH":
            payload = getattr(event, "__dict__", {})
            region = str(payload.get("region", ""))
            goal = (
                f"Mitigate latency breach in {region or entity_id}. "
                f"KPI {payload.get('kpi', 'latency_ms')} = "
                f"{payload.get('value', 0):.1f} (threshold "
                f"{payload.get('threshold', 0):.1f})."
            )
        elif evt_type == "NF_FAILED":
            payload = getattr(event, "__dict__", {})
            goal = (
                f"Recover failed NF '{entity_id}' "
                f"(cause: {payload.get('cause', 'unknown')})."
            )
        else:
            return

        # De-dup key
        key = f"{evt_type}:{entity_id}:{region}"
        if key in self._in_flight:
            logger.debug("AutoTrigger: already handling %s — skipping", key)
            return

        correlation_id = f"auto_{evt_type.lower()[:6]}_{entity_id[:8]}"
        self._in_flight[key] = correlation_id
        logger.info("AutoTrigger: launching autonomous workflow '%s'", goal[:80])

        async def _run_and_cleanup() -> None:
            try:
                await self._engine.start(
                    goal=goal,
                    trigger="observer",
                    correlation_id=correlation_id,
                )
            except Exception:
                logger.exception("AutoTrigger workflow failed for key %s", key)
            finally:
                self._in_flight.pop(key, None)

        task = asyncio.create_task(_run_and_cleanup())
        # Keep a reference so the task isn't garbage-collected (RUF006)
        self._task_refs: set = getattr(self, "_task_refs", set())
        self._task_refs.add(task)
        task.add_done_callback(self._task_refs.discard)

    def cancel(self) -> None:
        if self._subscription:
            self._subscription.cancel()

    @property
    def in_flight_count(self) -> int:
        return len(self._in_flight)

    @property
    def autonomy_enabled(self) -> bool:
        return self._autonomy_enabled

    def set_autonomy(self, enabled: bool) -> None:
        self._autonomy_enabled = enabled
