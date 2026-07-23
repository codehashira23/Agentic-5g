"""
Domain: Ports (interfaces) for the Service Enablement Layer.

Owning docs: 03-architecture.md §7, 08-services.md §11
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.services.models import ServiceDescriptor
from app.domain.services.policy import Policy


# ---------------------------------------------------------------------------
# ServiceRegistry — port for registering and discovering services
# ---------------------------------------------------------------------------
@runtime_checkable
class ServiceRegistry(Protocol):
    """
    Port: register descriptors, discover services by name/filter.
    Implemented in application/sel/registry.py (C080).
    """

    def register(self, descriptor: ServiceDescriptor) -> None:
        """Register a service descriptor (idempotent by name)."""
        ...

    def get(self, name: str) -> ServiceDescriptor | None:
        """Return the descriptor for a service by exact name."""
        ...

    def list_services(
        self,
        kind: str | None = None,
        owner_nf: str | None = None,
        tag: str | None = None,
    ) -> list[ServiceDescriptor]:
        """Return descriptors matching the given filters."""
        ...

    def all(self) -> list[ServiceDescriptor]:
        """Return all registered descriptors."""
        ...


# ---------------------------------------------------------------------------
# PolicyStore — port for loading/persisting policy configuration
# ---------------------------------------------------------------------------
@runtime_checkable
class PolicyStore(Protocol):
    """
    Port: load and update policy configuration from the DB.
    Implemented in infrastructure/db/repos/policy_store.py (C069).
    """

    async def load_all(self) -> list[Policy]:
        """Return all policies (enabled and disabled)."""
        ...

    async def save(self, policy: Policy) -> None:
        """Upsert a policy (used during seed and Settings edits)."""
        ...

    async def get(self, policy_id: str) -> Policy | None:
        """Return one policy by id, or None."""
        ...
