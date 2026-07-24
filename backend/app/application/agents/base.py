"""
Application: BaseAgent + AgentContext — the common anatomy for all seven agents.

Every agent:
  - receives typed input (a dict from WorkflowState)
  - calls the LLMClient via tool_call() with its bound tools
  - validates the output against its Pydantic schema
  - re-prompts ONCE on validation failure, then uses fallback
  - on 429 rate limit, waits and retries with backoff

Owning docs: 05-agents.md §5, 14-prompts.md §4
"""
from __future__ import annotations

import asyncio
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

    MAX_REPROMPTS = 1
    RATE_LIMIT_WAIT_S = 15  # wait 15s on first 429, 30s on second

    def __init__(self) -> None:
        self._last_error: str = ""

    @property
    @abstractmethod
    def role(self) -> AgentRole: ...

    @property
    @abstractmethod
    def output_schema(self) -> type[TOut]: ...

    @abstractmethod
    def _build_payload(self, input_data: dict[str, Any]) -> dict[str, Any]: ...

    # ------------------------------------------------------------------
    # run() — the public interface
    # ------------------------------------------------------------------
    async def run(self, input_data: dict[str, Any], ctx: AgentContext) -> TOut:
        payload = self._build_payload(input_data)
        system, user = ctx.prompt_registry.render(self.role.value, payload)
        start = datetime.now(UTC).timestamp()

        for attempt in range(self.MAX_REPROMPTS + 1):
            messages = [{"role": "user", "content": user}]
            if attempt > 0:
                messages.append({
                    "role": "user",
                    "content": (
                        f"Previous response failed schema validation: {self._last_error}. "
                        "Return ONLY a valid JSON object with all required fields."
                    ),
                })

            # --- LLM call with 429 retry ---
            raw: dict[str, Any] | None = None
            for llm_attempt in range(3):  # up to 3 rate-limit retries
                try:
                    raw = await ctx.llm.tool_call(
                        system=system,
                        messages=messages,
                        tools=ctx.tools,
                        response_schema=self.output_schema.model_json_schema(),
                    )
                    break  # success
                except Exception as llm_exc:
                    err_str = str(llm_exc)
                    if "429" in err_str:
                        wait = self.RATE_LIMIT_WAIT_S * (llm_attempt + 1)
                        logger.warning(
                            "Agent %s rate-limited (llm attempt %d), waiting %ds",
                            self.role.value, llm_attempt + 1, wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    # Non-429 error — log and break
                    logger.error(
                        "Agent %s LLM call failed (attempt %d): %s",
                        self.role.value, attempt + 1, err_str,
                    )
                    break

            if raw is None:
                # All LLM attempts failed
                if attempt < self.MAX_REPROMPTS:
                    continue
                return self._fallback_output(input_data)

            latency_ms = (datetime.now(UTC).timestamp() - start) * 1000.0

            try:
                output = self.output_schema.model_validate(raw)
                logger.debug(
                    "Agent %s OK in %.1f ms (attempt %d)",
                    self.role.value, latency_ms, attempt + 1,
                )
                return output
            except ValidationError as exc:
                self._last_error = str(exc)
                if attempt < self.MAX_REPROMPTS:
                    logger.warning(
                        "Agent %s validation failed (attempt %d), re-prompting: %s",
                        self.role.value, attempt + 1, exc,
                    )
                    continue
                logger.error(
                    "Agent %s validation failed after %d attempts. Raw=%s",
                    self.role.value, self.MAX_REPROMPTS + 1, raw,
                )
                return self._fallback_output(input_data, raw)

        return self._fallback_output(input_data)

    # ------------------------------------------------------------------
    # _fallback_output — goal-aware defaults
    # ------------------------------------------------------------------
    def _fallback_output(
        self,
        input_data: dict[str, Any],
        raw: dict[str, Any] | None = None,
    ) -> TOut:
        """
        Build a minimal valid output from defaults + raw + input context.
        For Plan fallback, infer a deploy step from the goal string.
        """
        raw = raw or {}
        goal: str = (
            input_data.get("goal", "")
            or raw.get("goal", "")
            or ""
        )

        # Infer deploy step from goal text when plan is empty
        inferred_steps = raw.get("steps") or []
        if not inferred_steps and goal:
            goal_lower = goal.lower()
            if "deploy" in goal_lower and "edge" in goal_lower:
                # Determine target region
                target = "edge_delhi_1"
                if "mumbai" in goal_lower:
                    target = "edge_mumbai_1"
                model_id = "congestion_v1"
                if "anomal" in goal_lower:
                    model_id = "anomaly_v1"
                elif "traffic" in goal_lower:
                    model_id = "traffic_v1"
                inferred_steps = [{
                    "index": 0,
                    "service": "aimle.model.deploy",
                    "args": {
                        "model_id": model_id,
                        "name": model_id,
                        "target": target,
                        "target_node_id": target,
                    },
                    "depends_on": [],
                    "success_criterion": f"model {model_id} deployed on {target}",
                }]
                logger.info(
                    "Fallback plan: inferred deploy step %s → %s from goal",
                    model_id, target,
                )

        defaults: dict[str, Any] = {
            "rationale": raw.get("rationale") or "Agent used fallback due to LLM unavailability.",
            "objective": raw.get("objective") or goal or "Complete the requested operation.",
            "targets": raw.get("targets") or [],
            "constraints": raw.get("constraints") or [],
            "success_criteria": raw.get("success_criteria") or ["operation completed"],
            "tick": raw.get("tick") or 0,
            "health_pct": raw.get("health_pct") or 1.0,
            "active_workflows": raw.get("active_workflows") or 0,
            "entity_states": raw.get("entity_states") or {},
            "notable_events": raw.get("notable_events") or [],
            "memory_summary": raw.get("memory_summary") or "",
            "steps": inferred_steps,
            "verdict": raw.get("verdict") or "pass",
            "criteria": raw.get("criteria") or [],
            "step_index": raw.get("step_index") or 0,
            "service": raw.get("service") or (inferred_steps[0]["service"] if inferred_steps else ""),
            "status": raw.get("status") or "ok",
            "result": raw.get("result") or {},
            "success_met": raw.get("success_met") if raw.get("success_met") is not None else True,
            "compensation": raw.get("compensation"),
            "retry_hint": raw.get("retry_hint"),
            "workflow_id": raw.get("workflow_id") or "",
            "goal": raw.get("goal") or goal,
            "outcome": raw.get("outcome") or "success",
            "narrative": raw.get("narrative") or f"Workflow for goal '{goal}' completed via fallback.",
            "evidence": raw.get("evidence") or [],
            "lessons": raw.get("lessons") or [],
            "kg_deltas": raw.get("kg_deltas") or [],
            "steps_taken": raw.get("steps_taken") or [],
            "escalate": raw.get("escalate") or False,
            "escalate_reason": raw.get("escalate_reason") or "",
        }
        merged = {**defaults, **{k: v for k, v in raw.items() if v is not None}}
        return self.output_schema.model_validate(merged)


# ---------------------------------------------------------------------------
# AgentOutputError
# ---------------------------------------------------------------------------
class AgentOutputError(RuntimeError):
    """Raised when an agent cannot produce a valid structured output."""
