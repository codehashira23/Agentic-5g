"""
AgentOrchestrator — wires agents to workflow nodes and provides make_context().

Holds references to all seven agents, the SEL invoker, and the twin service.
Passed as the `orchestrator` argument to every node function.

Owning docs: 05-agents.md §8, 13-workflow-engine.md §15
"""
from __future__ import annotations

from typing import Any

from app.application.agents.base import AgentContext
from app.application.agents.documentation import DocumentationAgent
from app.application.agents.executor import ExecutorAgent
from app.application.agents.memory_agent import MemoryAgent
from app.application.agents.observer import ObserverAgent, ValidatorAgent
from app.application.agents.optimizer import OptimizerAgent
from app.application.agents.planner import InterpretationAgent, PlannerAgent
from app.application.agents.prompts.registry import PromptRegistry, get_registry
from app.application.agents.recovery import RecoveryAgent
from app.application.sel.tools import ToolAdapter
from app.domain.agents.models import AgentRole
from app.domain.agents.ports import LLMClient


class AgentOrchestrator:
    """
    Central wiring point: holds all agents + shared infrastructure.
    Passed to every workflow node so nodes stay thin.
    """

    def __init__(
        self,
        llm: LLMClient,
        invoker: Any,          # ServiceInvoker
        registry: Any,         # ServiceRegistry
        twin_service: Any,     # TwinService
        prompt_registry: PromptRegistry | None = None,
    ) -> None:
        self._llm = llm
        self.invoker = invoker
        self.registry = registry
        self.twin_service = twin_service
        self._prompt_registry = prompt_registry or get_registry()

        # Tool adapter for per-role tool scoping
        self._tool_adapter = ToolAdapter(registry)

        # Instantiate all seven agents
        self.observer = ObserverAgent()
        self.validator = ValidatorAgent()
        self.interpreter = InterpretationAgent()
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.optimizer = OptimizerAgent()
        self.recovery = RecoveryAgent()
        self.documenter = DocumentationAgent()
        self.memory = MemoryAgent()

    def make_context(self, role_str: str) -> AgentContext:
        """Build an AgentContext scoped to the given role."""
        try:
            role = AgentRole(role_str)
        except ValueError:
            role = AgentRole.PLANNER  # fallback

        tools = self._tool_adapter.tools_for(role)
        return AgentContext(
            llm=self._llm,
            tools=tools,
            correlation_id=None,
            prompt_registry=self._prompt_registry,
        )
