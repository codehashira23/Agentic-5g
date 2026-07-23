"""
Domain: Ports (interfaces) for the Digital Twin layer.

These are abstract Protocol definitions — the contracts the domain
declares and the infrastructure layer must satisfy (ADR-6, P7).

The domain depends ONLY on these interfaces, never on adapters.
Adapters are bound at the composition root (app/main.py + api/deps.py).

Owning docs: 03-architecture.md §7, 06-digital-twin.md §17
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.twin.events import DomainEvent
from app.domain.twin.kpi import KpiSample
from app.domain.twin.network_twin import TwinSnapshot


# ---------------------------------------------------------------------------
# TwinRepository — persistence port for the Digital Twin
# ---------------------------------------------------------------------------
@runtime_checkable
class TwinRepository(Protocol):
    """
    Persistence port for twin snapshots and KPI history.
    Implemented in infrastructure/db/repos/twin_repo.py (C068).
    """

    async def save_snapshot(self, snapshot: TwinSnapshot) -> None:
        """Persist a full twin snapshot for fast restart."""
        ...

    async def load_snapshot(self) -> TwinSnapshot | None:
        """Load the most recent persisted snapshot, or None."""
        ...

    async def append_kpis(self, samples: list[KpiSample]) -> None:
        """Write-behind batch of KPI samples (06-digital-twin.md §15)."""
        ...

    async def get_kpi_history(
        self,
        entity_id: str,
        kpi: str,
        limit: int = 100,
    ) -> list[KpiSample]:
        """Return the most recent KPI samples for one entity/KPI."""
        ...

    async def persist_event(self, event: DomainEvent) -> None:
        """Write-through persist one domain event (lossless for critical events)."""
        ...
