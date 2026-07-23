"""
C050: Tests that the port Protocol definitions are well-formed.

Verifies:
 - Each Protocol is @runtime_checkable and importable
 - Concrete stub implementations satisfy the Protocols via isinstance()
 - Port interfaces import cleanly with zero framework imports
"""
from __future__ import annotations

from typing import Any

from app.domain.agents.memory import KnowledgeEdge, KnowledgeNode, MemoryRecord
from app.domain.agents.models import MemoryScope
from app.domain.agents.ports import (
    EventBus,
    LLMClient,
    MemoryStore,
    Rng,
    WorkflowRepository,
)
from app.domain.services.ports import PolicyStore, ServiceRegistry
from app.domain.twin.kpi import KpiSample, KpiName
from app.domain.twin.ports import TwinRepository


# ---------------------------------------------------------------------------
# Minimal stub implementations for isinstance() checks
# ---------------------------------------------------------------------------

class StubTwinRepo:
    async def save_snapshot(self, snapshot: Any) -> None: ...
    async def load_snapshot(self) -> None: return None
    async def append_kpis(self, samples: list) -> None: ...
    async def get_kpi_history(self, entity_id, kpi, limit=100): return []
    async def persist_event(self, event: Any) -> None: ...


class StubServiceRegistry:
    def register(self, descriptor: Any) -> None: ...
    def get(self, name: str) -> None: return None
    def list_services(self, kind=None, owner_nf=None, tag=None): return []
    def all(self): return []


class StubPolicyStore:
    async def load_all(self): return []
    async def save(self, policy: Any) -> None: ...
    async def get(self, policy_id: str) -> None: return None


class StubMemoryStore:
    async def save_record(self, record: Any) -> None: ...
    async def get_records(self, scope, limit=20, workflow_id=None): return []
    async def get_record(self, record_id: str) -> None: return None
    async def upsert_node(self, node: Any) -> None: ...
    async def upsert_edge(self, edge: Any) -> None: ...
    async def get_neighbourhood(self, node_id: str, depth=1): return {}


class StubWorkflowRepo:
    async def save_workflow(self, workflow_id: str, data: dict) -> None: ...
    async def get_workflow(self, workflow_id: str) -> None: return None
    async def list_workflows(self, status=None, limit=50): return []
    async def append_trace(self, trace_row: dict) -> None: ...
    async def get_trace(self, workflow_id: str): return []
    async def save_step(self, step_row: dict) -> None: ...
    async def get_steps(self, workflow_id: str): return []


class StubLLMClient:
    async def complete(self, system, messages, **kw): return ""
    async def tool_call(self, system, messages, tools, response_schema=None, **kw):
        return {}


class StubRng:
    def for_tick(self, tick: int) -> Any: return self
    def reseed(self, seed: int) -> None: ...


class StubEventBus:
    async def publish(self, event: Any) -> None: ...
    def subscribe(self, event_types, handler) -> Any: return None


# ---------------------------------------------------------------------------
# Protocol conformance tests (isinstance with @runtime_checkable)
# ---------------------------------------------------------------------------
class TestProtocolConformance:
    def test_twin_repository_protocol(self) -> None:
        assert isinstance(StubTwinRepo(), TwinRepository)

    def test_service_registry_protocol(self) -> None:
        assert isinstance(StubServiceRegistry(), ServiceRegistry)

    def test_policy_store_protocol(self) -> None:
        assert isinstance(StubPolicyStore(), PolicyStore)

    def test_memory_store_protocol(self) -> None:
        assert isinstance(StubMemoryStore(), MemoryStore)

    def test_workflow_repository_protocol(self) -> None:
        assert isinstance(StubWorkflowRepo(), WorkflowRepository)

    def test_llm_client_protocol(self) -> None:
        assert isinstance(StubLLMClient(), LLMClient)

    def test_rng_protocol(self) -> None:
        assert isinstance(StubRng(), Rng)

    def test_event_bus_protocol(self) -> None:
        assert isinstance(StubEventBus(), EventBus)


# ---------------------------------------------------------------------------
# Non-conforming classes do NOT satisfy the protocol
# ---------------------------------------------------------------------------
class TestProtocolRejection:
    def test_empty_class_not_twin_repo(self) -> None:
        class Empty: pass
        assert not isinstance(Empty(), TwinRepository)

    def test_partial_impl_not_memory_store(self) -> None:
        class Partial:
            async def save_record(self, r): ...
            # missing get_records, upsert_node, etc.
        assert not isinstance(Partial(), MemoryStore)

    def test_empty_class_not_llm_client(self) -> None:
        class Empty: pass
        assert not isinstance(Empty(), LLMClient)

    def test_empty_class_not_event_bus(self) -> None:
        class Empty: pass
        assert not isinstance(Empty(), EventBus)


# ---------------------------------------------------------------------------
# Import-cleanliness: no framework leaks into domain ports
# Verified by import-linter (C012); this test double-checks at runtime.
# ---------------------------------------------------------------------------
class TestNoDomainFrameworkImport:
    def test_twin_ports_module_has_no_sqlalchemy(self) -> None:
        import app.domain.twin.ports as m
        import sys
        # sqlalchemy must not be imported as a side-effect of loading this port
        assert "sqlalchemy" not in dir(m)

    def test_agent_ports_module_has_no_fastapi(self) -> None:
        import app.domain.agents.ports as m
        assert "fastapi" not in dir(m)

    def test_service_ports_module_has_no_sqlalchemy(self) -> None:
        import app.domain.services.ports as m
        assert "sqlalchemy" not in dir(m)
