"""
Application: Tool Adapter — exposes SEL services as LLM-callable JSON-schema tools.

Each registered ServiceDescriptor becomes a tool with:
  name        — the dotted service name
  description — the descriptor's description
  parameters  — JSON Schema object derived from the descriptor

Agents receive a scoped subset of tools based on their role (05-agents.md §7):
  - read_tools    : read-only services (Observer, Planner, Optimizer, Documentation)
  - action_tools  : action services (Executor, Recovery)
  - memory_tools  : memory services (Memory agent only)

The MCP publication seam (20-future-work.md Track 3): these tool dicts are
already in MCP-compatible shape — name, description, inputSchema.

Owning docs: 08-services.md §9
"""
from __future__ import annotations

from typing import Any

from app.application.sel.registry import ServiceRegistry
from app.domain.agents.models import AgentRole
from app.domain.services.models import ServiceDescriptor, ServiceKind

# ---------------------------------------------------------------------------
# Tool scoping per agent role
# ---------------------------------------------------------------------------
_READ_ROLES = {
    AgentRole.OBSERVER,
    AgentRole.PLANNER,
    AgentRole.OPTIMIZER,
    AgentRole.DOCUMENTATION,
}
_ACTION_ROLES = {AgentRole.EXECUTOR, AgentRole.RECOVERY}
_MEMORY_ROLES = {AgentRole.MEMORY}

# Memory service prefix
_MEMORY_PREFIXES = ("memory.", "knowledge.")


class ToolAdapter:
    """
    Converts ServiceDescriptors to JSON-schema tools for agent use.

    Usage:
        adapter = ToolAdapter(registry)
        tools = adapter.tools_for(AgentRole.PLANNER)
        # → [{"name": "nrf.discover", "description": "...", "parameters": {...}}, ...]
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self._registry = registry

    def tools_for(self, role: AgentRole) -> list[dict[str, Any]]:
        """Return the tool list appropriate for the given agent role."""
        tools: list[dict[str, Any]] = []
        for desc in self._registry.all():
            if self._role_can_use(role, desc):
                tools.append(self._to_tool(desc))
        return tools

    def all_tools(self) -> list[dict[str, Any]]:
        return [self._to_tool(d) for d in self._registry.all()]

    def tool_for(self, service_name: str) -> dict[str, Any] | None:
        desc = self._registry.get(service_name)
        return self._to_tool(desc) if desc else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _role_can_use(self, role: AgentRole, desc: ServiceDescriptor) -> bool:
        """Apply tool scoping rules (05-agents.md §7)."""
        is_memory = any(
            desc.name.startswith(p) for p in _MEMORY_PREFIXES
        )
        if role in _MEMORY_ROLES:
            return True   # Memory agent can use everything
        if is_memory and desc.kind == ServiceKind.ACTION:
            return False  # Only Memory agent gets memory-write tools
        if role in _READ_ROLES:
            return desc.kind == ServiceKind.READ or is_memory
        if role in _ACTION_ROLES:
            return desc.kind in (ServiceKind.READ, ServiceKind.ACTION)
        return False

    @staticmethod
    def _to_tool(desc: ServiceDescriptor) -> dict[str, Any]:
        """
        Produce a minimal JSON-schema tool dict.

        In production, the `parameters` schema is derived from the service's
        Pydantic input_model (registered in application/sel/services/*).
        Here we produce a generic open schema; C086 will populate real schemas.
        """
        return {
            "name": desc.name,
            "description": desc.description or f"Call {desc.name}",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            },
            "kind": desc.kind.value,
            "owner_nf": desc.owner_nf,
            "spec_ref": desc.spec_ref,
            "compensation": desc.compensation,
        }
