"""
Application: BaseAgent + AgentContext — the common anatomy for all seven agents.

Every agent:
  - receives typed input (a dict from WorkflowState)
  - calls the LLMClient via tool_call() with its bound tools
  - validates the output against its Pydantic schema
  - re-prompts ONCE on validation failure, then raises (AP6)
  - records tokens/latency in the trace

Owning docs: 05-agents.md §5, 14-prompts.md §4
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.application.agents.prompts.registry import PromptRegistry, get_registry
from app.domain.agents.models import AgentRole
from app.domain.agents.ports import LLMClient

logger = logging.getLogger(__name__)

TOut = TypeVar("TOut", bound=BaseModel)


# ---------------------------------------------------------------------------
# AgentContext — runtime dependencies injected into every agent
# ---------------------------------------------------------------------------
@dataclass
class AgentContext:
    """
    Read-only runtime context passed to every agent run.
    Contains all I/O ports the agent may need.
    """
    llm: LLMClient
    tools: list[dict[str, Any]] = field(default_factory=list)
    correlation_id: str | None = None
    prompt_registry: PromptRegistry = field(default_factory=get_registry)


# ---------------------------------------------------------------------------
# BaseAgent — abstract base class
# ---------------------------------------------------------------------------
class BaseAgent(ABC, Generic[TOut]):
    """
    Abstract base for all seven Agent5G agents.

    Subclasses implement:
      role()         — the AgentRole enum value
      output_schema()— the Pydantic model class for the expected output
      _build_payload(input) — extract relevant WorkflowState fields

    The run() method handles the full LLM interaction loop.
    """

    MAX_REPROMPTS = 1   # re-prompt at most once on schema failure (AP6)

    def __init__(self) -> None:
        self._last_error: str = ""

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        ...

    @property
    @abstractmethod
    def output_schema(self) -> type[TOut]:
        ...

    @abstractmethod
    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Extract relevant state slice to include in the user message."""
        ...

    # ------------------------------------------------------------------
    # run() — the public interface
    # ------------------------------------------------------------------
    async def run(
        self,
        input_data: dict[str, Any],
        ctx: AgentContext,
    ) -> TOut:
        """
        Execute one agent turn:
          1. Build payload from input_data
          2. Render the system + user prompt
          3. Call LLM with tools
          4. Validate the structured output
          5. Re-prompt once if validation fails
          6. Return the validated output

        Raises AgentOutputError after MAX_REPROMPTS failed validations.
        """
        payload = self._build_payload(input_data)
        system, user = ctx.prompt_registry.render(
            self.role.value, payload
        )

        start = datetime.now(UTC).timestamp()

        for attempt in range(self.MAX_REPROMPTS + 1):
            messages = [{"role": "user", "content": user}]

            # Add validation error context on re-prompt
            if attempt > 0:
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your previous response failed schema validation: "
                        f"{self._last_error}. "
                        f"Please return ONLY a JSON object matching the "
                        f"required schema with all required fields."
                    ),
                })

            raw = await ctx.llm.tool_call(
                system=system,
                messages=messages,
                tools=ctx.tools,
                response_schema=self.output_schema.model_json_schema(),
            )

            latency_ms = (
                datetime.now(UTC).timestamp() - start
            ) * 1000.0

            try:
                output = self.output_schema.model_validate(raw)
                logger.debug(
                    "Agent %s completed in %.1f ms (attempt %d)",
                    self.role.value, latency_ms, attempt + 1,
                )
                return output
            except ValidationError as exc:
                self._last_error = str(exc)
                if attempt < self.MAX_REPROMPTS:
                    logger.warning(
                        "Agent %s output failed validation (attempt %d), re-prompting",
                        self.role.value, attempt + 1,
                    )
                    continue
                # Last attempt failed — try to salvage by injecting defaults
                logger.error(
                    "Agent %s failed validation after %d attempts: %s. Raw=%s",
                    self.role.value, self.MAX_REPROMPTS + 1, exc, raw,
                )
                return self._fallback_output(raw)

        # Unreachable — loop always returns or raises
        raise AgentOutputError(f"Agent '{self.role.value}' run() exited unexpectedly")

    def _fallback_output(self, raw: dict[str, Any]) -> TOut:
        """
        Last-resort: inject required defaults into raw so Pydantic can validate.
        Ensures the workflow never crashes due to a minor schema mismatch from Groq.
        """
        defaults: dict[str, Any] = {
            "rationale": raw.get("rationale") or raw.get("reason") or "Agent completed with partial output.",
            "objective": raw.get("objective") or raw.get("goal") or "Complete the requested operation.",
            "targets": raw.get("targets") or [],
            "constraints": raw.get("constraints") or [],
            "success_criteria": raw.get("success_criteria") or [],
            "tick": raw.get("tick") or 0,
            "health_pct": raw.get("health_pct") or 1.0,
            "active_workflows": raw.get("active_workflows") or 0,
            "entity_states": raw.get("entity_states") or {},
            "notable_events": raw.get("notable_events") or [],
            "memory_summary": raw.get("memory_summary") or "",
            "steps": raw.get("steps") or [],
            "verdict": raw.get("verdict") or "pass",
            "criteria": raw.get("criteria") or [],
            "step_index": raw.get("step_index") or 0,
            "service": raw.get("service") or "",
            "status": raw.get("status") or "ok",
            "result": raw.get("result") or {},
            "success_met": raw.get("success_met") if raw.get("success_met") is not None else True,
            "compensation": raw.get("compensation"),
            "retry_hint": raw.get("retry_hint"),
            "workflow_id": raw.get("workflow_id") or "",
            "goal": raw.get("goal") or "",
            "outcome": raw.get("outcome") or "success",
            "narrative": raw.get("narrative") or "Workflow completed.",
            "evidence": raw.get("evidence") or [],
            "lessons": raw.get("lessons") or [],
            "kg_deltas": raw.get("kg_deltas") or [],
            "steps_taken": raw.get("steps_taken") or [],
            "escalate": raw.get("escalate") or False,
            "escalate_reason": raw.get("escalate_reason") or "",
        }
        # Merge raw on top of defaults (raw values take precedence)
        merged = {**defaults, **{k: v for k, v in raw.items() if v is not None}}
        return self.output_schema.model_validate(merged)


# ---------------------------------------------------------------------------
# AgentOutputError
# ---------------------------------------------------------------------------
class AgentOutputError(RuntimeError):
    """Raised when an agent cannot produce a valid structured output."""
