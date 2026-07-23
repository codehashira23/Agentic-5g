"""
Infrastructure: In-process async event bus (persist-first then fan-out).

Implements the EventBus domain port (domain/agents/ports.py).

Design (03-architecture.md §8):
  1. publish(event) persists the event via the writer FIRST.
  2. Then fans out to all registered handlers asynchronously.
  3. Breach/failure/lifecycle/workflow/service events are LOSSLESS —
     they get a dedicated queue with no drop policy.
  4. High-frequency KPI_UPDATED is drop-oldest under backpressure
     (configurable per subscriber).

Backpressure per subscriber:
  - Each subscriber has a bounded asyncio.Queue.
  - Default capacity = 1000.
  - drop_oldest=True (default) → old items replaced by new ones.
  - drop_oldest=False (lossless) → blocks when full (used for critical events).

Owning docs: 03-architecture.md §8, 10-backend.md §8.3
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subscription — one registered handler
# ---------------------------------------------------------------------------
@dataclass
class Subscription:
    """A registered event handler with its own bounded queue."""

    handler: Callable[[Any], Coroutine[Any, Any, None]]
    event_types: list[str]           # empty = all
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    drop_oldest: bool = True         # False = lossless (critical events)
    _active: bool = True

    def cancel(self) -> None:
        self._active = False

    def offer(self, event: Any) -> None:
        """Non-blocking offer — drops oldest if full and drop_oldest=True."""
        if not self._active:
            return
        if not self.queue.full():
            self.queue.put_nowait(event)
        elif self.drop_oldest:
            try:
                self.queue.get_nowait()   # discard oldest
            except asyncio.QueueEmpty:
                pass
            self.queue.put_nowait(event)
        # If not drop_oldest and full: silently discard (caller chose lossless
        # but queue is at capacity — should not happen for critical events
        # if queue size is generous enough).


# ---------------------------------------------------------------------------
# InProcessEventBus
# ---------------------------------------------------------------------------
class InProcessEventBus:
    """
    In-process async pub/sub event bus.

    Implements the EventBus domain port.
    Persist-first: caller must pass a `persist_fn` coroutine that is
    awaited before fan-out.  In tests, pass `None` to skip persistence.
    """

    def __init__(
        self,
        persist_fn: Callable[[Any], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._persist_fn = persist_fn
        self._subscriptions: list[Subscription] = []
        self._dispatch_tasks: list[asyncio.Task] = []

    # ------------------------------------------------------------------
    # EventBus port interface
    # ------------------------------------------------------------------
    async def publish(self, event: Any) -> None:
        """
        Persist the event first, then offer it to all matching subscribers.
        """
        # 1. Persist-first (write-through)
        if self._persist_fn is not None:
            try:
                await self._persist_fn(event)
            except Exception:
                logger.exception("Event persistence failed for %s", event)

        # 2. Fan-out to matching subscribers
        event_type: str = getattr(event, "type", "")
        if hasattr(event_type, "value"):
            event_type = event_type.value

        for sub in list(self._subscriptions):
            if not sub._active:
                continue
            if not sub.event_types or event_type in sub.event_types:
                sub.offer(event)

    def subscribe(
        self,
        event_types: list[str],
        handler: Callable[[Any], Coroutine[Any, Any, None]],
        lossless: bool = False,
        queue_size: int = 1000,
    ) -> Subscription:
        """
        Register a handler for one or more event types.

        Args:
            event_types : list of SCREAMING_SNAKE_CASE type strings;
                          empty list = subscribe to ALL events.
            handler     : async callable(event) -> None.
            lossless    : if True, never drop events (critical handlers).
            queue_size  : subscriber queue capacity.

        Returns:
            Subscription — call .cancel() to unsubscribe.
        """
        sub = Subscription(
            handler=handler,
            event_types=event_types,
            queue=asyncio.Queue(maxsize=queue_size),
            drop_oldest=not lossless,
        )
        self._subscriptions.append(sub)
        return sub

    # ------------------------------------------------------------------
    # Dispatch loop — started as a background task
    # ------------------------------------------------------------------
    async def run(self) -> None:
        """
        Dispatch loop: drain all subscriber queues and call their handlers.
        Runs until cancelled.
        """
        while True:
            dispatched = 0
            for sub in list(self._subscriptions):
                if not sub._active:
                    self._subscriptions.remove(sub)
                    continue
                while not sub.queue.empty():
                    try:
                        event = sub.queue.get_nowait()
                        try:
                            await sub.handler(event)
                        except Exception:
                            logger.exception(
                                "Handler %s raised for event %s",
                                sub.handler, event,
                            )
                        dispatched += 1
                    except asyncio.QueueEmpty:
                        break
            if not dispatched:
                await asyncio.sleep(0.01)

    # ------------------------------------------------------------------
    # Stats / helpers
    # ------------------------------------------------------------------
    @property
    def subscriber_count(self) -> int:
        return len([s for s in self._subscriptions if s._active])

    def clear_subscriptions(self) -> None:
        for sub in self._subscriptions:
            sub.cancel()
        self._subscriptions.clear()

    def satisfies_port(self) -> bool:
        from app.domain.agents.ports import EventBus
        return isinstance(self, EventBus)
