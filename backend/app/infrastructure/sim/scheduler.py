"""
Infrastructure: Simulation tick scheduler.

Emits SIM_TICK events at a configurable interval.
Separated from the twin (clock ≠ state) so tests can use a manual clock.

Controls:
  start()  — begin ticking
  pause()  — halt without losing tick counter
  step(n)  — advance exactly n ticks while paused (test-friendly)
  reset()  — set tick back to 0

The TwinService subscribes to SIM_TICK and advances the twin.
Owning docs: 10-backend.md §8.6, 06-digital-twin.md §7
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any


@dataclass
class SimTick:
    """Minimal SIM_TICK event emitted by the scheduler."""
    type: str = "SIM_TICK"
    tick: int = 0


class SimScheduler:
    """
    Configurable tick clock for the Digital Twin simulation.

    Usage:
        scheduler = SimScheduler(tick_ms=1000, on_tick=my_handler)
        asyncio.create_task(scheduler.run())
        scheduler.start()
        ...
        scheduler.pause()
        await scheduler.step(n=5)   # manual advance in tests
    """

    def __init__(
        self,
        tick_ms: int = 1000,
        on_tick: Callable[[SimTick], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._tick_ms = tick_ms
        self._on_tick = on_tick
        self._tick = 0
        self._gate = asyncio.Event()     # set = running, clear = paused
        self._stop = False

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------
    def start(self) -> None:
        self._gate.set()

    def pause(self) -> None:
        self._gate.clear()

    def reset(self) -> None:
        self._tick = 0
        self._gate.clear()

    def set_tick_ms(self, tick_ms: int) -> None:
        self._tick_ms = max(1, tick_ms)

    async def stop(self) -> None:
        self._stop = True
        self._gate.set()   # unblock the run loop

    async def step(self, n: int = 1) -> None:
        """Advance exactly n ticks, emitting SIM_TICK for each."""
        for _ in range(n):
            self._tick += 1
            await self._emit()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def tick(self) -> int:
        return self._tick

    @property
    def running(self) -> bool:
        return self._gate.is_set()

    # ------------------------------------------------------------------
    # Background task
    # ------------------------------------------------------------------
    async def run(self) -> None:
        """
        Main loop — runs until stop() is called.
        Waits on the gate (pause/start) and sleeps tick_ms between ticks.
        """
        while not self._stop:
            await self._gate.wait()
            if self._stop:
                break
            self._tick += 1
            await self._emit()
            await asyncio.sleep(self._tick_ms / 1000.0)

    async def _emit(self) -> None:
        if self._on_tick is not None:
            try:
                await self._on_tick(SimTick(tick=self._tick))
            except Exception:
                pass   # never let a handler crash the scheduler
