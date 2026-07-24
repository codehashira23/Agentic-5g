"""
Application: Twin Service — the use-case layer over the Digital Twin.

Responsibilities:
  on_tick(tick)       — advance the twin, emit/persist events
  snapshot()          — return the TwinSnapshot read model
  apply_command(s,a)  — route a service call to the owning NF
  control(action)     — start / pause / step / reset the simulation

The Sim Scheduler calls on_tick; the SEL Invoker calls apply_command;
the API calls snapshot() and control().

External mutation enters ONLY through apply_command (invariant TP6).
The tick loop is the only internal mutator.

Owning docs: 06-digital-twin.md §7, 10-backend.md §8
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, update

from app.domain.twin.events import DomainEvent
from app.domain.twin.network_twin import NetworkTwin, TwinSnapshot
from app.infrastructure.bus.bus import InProcessEventBus
from app.infrastructure.db.engine import Database
from app.infrastructure.db.models import EventRow, KpiRow, SimulationRow
from app.infrastructure.rng.rng import RngService
from app.infrastructure.writer.writer import PersistenceWriter, WriteOp

logger = logging.getLogger(__name__)

# Max KPI samples to buffer before write-behind flush
_KPI_BATCH_SIZE = 5


class TwinService:
    """
    Application-layer coordinator for the Digital Twin.

    Thin use-case class: it delegates reasoning to NetworkTwin and
    persistence/eventing to the writer and bus.
    """

    def __init__(
        self,
        twin: NetworkTwin,
        rng: RngService,
        bus: InProcessEventBus,
        writer: PersistenceWriter,
        db: Database,
        run_id: int = 1,
    ) -> None:
        self._twin = twin
        self._rng = rng
        self._bus = bus
        self._writer = writer
        self._db = db
        self._run_id = run_id
        self._kpi_buffer: list[dict[str, Any]] = []
        self._status = "stopped"

    # ------------------------------------------------------------------
    # on_tick — called by the Sim Scheduler on every SIM_TICK
    # ------------------------------------------------------------------
    async def on_tick(self, tick: int) -> list[DomainEvent]:
        """
        Advance the twin by one tick:
        1. Derive a seeded RNG stream for this tick.
        2. Call NetworkTwin.advance() → events.
        3. Persist: write-through discrete events, write-behind KPI samples.
        4. Publish all events on the bus.
        """
        stream = self._rng.for_tick(tick)
        events = self._twin.advance(stream, tick=tick)
        ts = datetime.now(UTC).isoformat()

        kpi_rows: list[dict[str, Any]] = []
        discrete_events: list[DomainEvent] = []

        for evt in events:
            evt_type = evt.type.value if hasattr(evt.type, "value") else str(evt.type)
            if evt_type == "KPI_UPDATED":
                # Write-behind: buffer KPI samples
                kpi_rows.append({
                    "node_id": getattr(evt, "entity_id", ""),
                    "kpi": getattr(evt, "kpi", ""),
                    "value": float(getattr(evt, "value", 0.0)),
                    "tick": tick,
                    "run_id": self._run_id,
                    "ts": ts,
                })
            else:
                # Write-through: discrete events persisted immediately
                discrete_events.append(evt)

        # Write-through: persist discrete events
        for evt in discrete_events:
            evt_type = evt.type.value if hasattr(evt.type, "value") else str(evt.type)
            payload = evt.model_dump(
                exclude={"type", "event_id", "correlation_id", "ts", "tick"}
            )
            await self._writer.submit(WriteOp(
                stmt=insert(EventRow).values(
                    type=evt_type,
                    correlation_id=evt.correlation_id,
                    entity_id=getattr(evt, "entity_id", None),
                    payload_json=json.dumps(payload, default=str),
                    tick=tick,
                    run_id=self._run_id,
                    ts=ts,
                )
            ))

        # Write-behind: accumulate KPI buffer, flush every tick
        self._kpi_buffer.extend(kpi_rows)
        if len(self._kpi_buffer) >= _KPI_BATCH_SIZE:
            await self._flush_kpis()
        # Always flush any remaining KPIs so Analytics page sees data immediately
        if self._kpi_buffer:
            await self._flush_kpis()

        # Publish all events on the bus
        for evt in events:
            await self._bus.publish(evt)

        # Update simulation tick in DB
        await self._writer.submit(WriteOp(
            stmt=update(SimulationRow)
            .where(SimulationRow.id == self._run_id)
            .values(tick=tick, status="running")
        ))

        return events

    async def _flush_kpis(self) -> None:
        """Flush the KPI buffer write-behind."""
        batch = self._kpi_buffer[:]
        self._kpi_buffer.clear()
        for row in batch:
            await self._writer.submit(WriteOp(
                stmt=insert(KpiRow).values(**row)
            ))

    # ------------------------------------------------------------------
    # snapshot — read model for agents and the UI
    # ------------------------------------------------------------------
    def snapshot(self) -> TwinSnapshot:
        return self._twin.snapshot()

    # ------------------------------------------------------------------
    # apply_command — external mutation (SEL Invoker path, invariant TP6)
    # ------------------------------------------------------------------
    def apply_command(
        self, service_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Route a service call to the owning NF in the twin."""
        return self._twin.apply_command(service_name, args)

    # ------------------------------------------------------------------
    # control — simulation lifecycle
    # ------------------------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        return {
            "status": self._status,
            "tick": self._twin.tick,
            "seed": self._twin.seed,
            "nf_count": self._twin.nf_count,
        }

    async def set_status(self, status: str) -> None:
        self._status = status
        await self._writer.submit(WriteOp(
            stmt=update(SimulationRow)
            .where(SimulationRow.id == self._run_id)
            .values(status=status)
        ))
