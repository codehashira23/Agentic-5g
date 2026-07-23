"""
Infrastructure: Provider-agnostic LLMClient implementations.

Three modes behind the LLMClient port (10-backend.md §8.4):
  replay  — serve saved fixtures keyed by request hash ($0, offline, default)
  record  — live call + save to fixtures (run once to author fixtures)
  live    — real provider call (free-tier; CST-1/CST-3)

Also provides FakeLLM for pure unit tests (canned outputs, no fixtures).

Added in A2:
  GroqClient — OpenAI-compatible HTTP client for Groq free tier.
               Activated when LLM__MODE=live and LLM__PROVIDER=groq.

Owning docs: 10-backend.md §8.4, 14-prompts.md §12
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class MissingFixtureError(RuntimeError):
    """Raised when replay mode cannot find a fixture for the request hash."""


class LLMProviderError(RuntimeError):
    """Raised when a live provider call fails."""


# ---------------------------------------------------------------------------
# FakeLLM — deterministic canned outputs for unit tests
# ---------------------------------------------------------------------------
class FakeLLM:
    """
    Deterministic LLM stand-in for unit/integration tests.
    No network, no fixtures — responses are registered in advance.
    """

    def __init__(self) -> None:
        self._responses: list[dict[str, Any]] = []
        self._call_count = 0

    def set_response(self, output: dict[str, Any]) -> None:
        self._responses.append(output)

    def set_responses(self, outputs: list[dict[str, Any]]) -> None:
        self._responses.extend(outputs)

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        self._call_count += 1
        if self._responses:
            r = self._responses.pop(0)
            return json.dumps(r)
        return '{"rationale": "FakeLLM default response"}'

    async def tool_call(
        self,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        response_schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self._call_count += 1
        if self._responses:
            return self._responses.pop(0)
        return {"rationale": "FakeLLM default tool response"}

    @property
    def call_count(self) -> int:
        return self._call_count

    def satisfies_port(self) -> bool:
        from app.domain.agents.ports import LLMClient
        return isinstance(self, LLMClient)


# ---------------------------------------------------------------------------
# GroqClient — real HTTP calls to Groq (OpenAI-compatible, free tier)
# ---------------------------------------------------------------------------
class GroqClient:
    """
    Live Groq inference via the OpenAI-compatible /chat/completions endpoint.

    Free tier: https://console.groq.com — sign in, create an API key (gsk_...).
    Recommended model: llama-3.1-8b-instant (fast, free, good at tool use).

    The agent sends a system prompt + user message.  We pack them into the
    OpenAI message format and return the assistant's text content, which the
    agent then parses as JSON (per the structured-output contract in AP2).
    """

    DEFAULT_TIMEOUT = 60.0       # seconds — Groq is fast; 60s is generous
    MAX_TOKENS      = 2048       # plenty for structured JSON outputs

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        base_url: str = "https://api.groq.com/openai/v1",
    ) -> None:
        self._api_key  = api_key
        self._model    = model
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # LLMClient port implementation
    # ------------------------------------------------------------------
    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Plain text completion — returns the assistant message content."""
        openai_msgs = [{"role": "system", "content": system}, *messages]
        payload = {
            "model": self._model,
            "messages": openai_msgs,
            "max_tokens": self.MAX_TOKENS,
            "temperature": 0.2,
        }
        data = await self._post("/chat/completions", payload)
        return data["choices"][0]["message"]["content"]

    async def tool_call(
        self,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        response_schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Ask Groq to return a structured JSON object matching the agent schema.

        We use JSON-mode (response_format=json_object) rather than the
        OpenAI function-calling protocol because Groq's free tier supports
        it reliably across all models.  The system prompt already instructs
        the model to return a JSON object matching the required schema.

        Returns the parsed dict directly — downstream agents validate it
        against their Pydantic model.
        """
        # Add a JSON reminder to the last user message so the model
        # doesn't output markdown code fences.
        amended_msgs = list(messages)
        if amended_msgs and amended_msgs[-1].get("role") == "user":
            amended_msgs[-1] = {
                "role": "user",
                "content": (
                    amended_msgs[-1]["content"]
                    + "\n\nRespond with a single valid JSON object only. "
                    "No markdown, no explanation outside the JSON."
                ),
            }

        openai_msgs = [{"role": "system", "content": system}, *amended_msgs]
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": openai_msgs,
            "max_tokens": self.MAX_TOKENS,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        data = await self._post("/chat/completions", payload)
        raw_text: str = data["choices"][0]["message"]["content"].strip()

        # Groq sometimes wraps the JSON in a markdown code block — strip it.
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            raw_text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Groq response was not valid JSON: %s", raw_text[:200])
            raise LLMProviderError(
                f"Groq returned non-JSON content: {raw_text[:200]}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------
    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        logger.debug("Groq → POST %s model=%s", url, payload.get("model"))
        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code == 401:
            raise LLMProviderError(
                "Groq: 401 Unauthorised — check your LLM__API_KEY in backend/.env"
            )
        if resp.status_code == 429:
            raise LLMProviderError(
                "Groq: 429 Rate limit — wait a moment and try again"
            )
        if resp.status_code != 200:
            raise LLMProviderError(
                f"Groq: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        return resp.json()  # type: ignore[no-any-return]

    def satisfies_port(self) -> bool:
        from app.domain.agents.ports import LLMClient
        return isinstance(self, LLMClient)


# ---------------------------------------------------------------------------
# ReplayClient — serve saved fixtures (offline, $0, deterministic)
# ---------------------------------------------------------------------------
class ReplayClient:
    """
    Replay LLM: serves saved JSON fixtures keyed by request hash.
    Raises MissingFixtureError on cache miss (never falls back to live).
    DEFAULT mode — all tests and demos use this.
    """

    def __init__(self, fixtures_dir: Path = Path("tests/fixtures/llm")) -> None:
        self._fixtures_dir = Path(fixtures_dir)

    def _hash(
        self,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str = "",
    ) -> str:
        payload = json.dumps(
            {"system": system, "messages": messages, "tools": tools, "model": model},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def _fixture_path(self, key: str) -> Path:
        return self._fixtures_dir / f"{key}.json"

    def _load(self, key: str) -> dict[str, Any]:
        path = self._fixture_path(key)
        if not path.exists():
            raise MissingFixtureError(
                f"No replay fixture for hash '{key}' at {path}. "
                "Run in 'record' mode once to create it."
            )
        return json.loads(path.read_text(encoding="utf-8"))

    def save_fixture(self, key: str, response: dict[str, Any]) -> None:
        self._fixtures_dir.mkdir(parents=True, exist_ok=True)
        self._fixture_path(key).write_text(
            json.dumps(response, indent=2), encoding="utf-8"
        )

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        key = self._hash(system, messages, [], kwargs.get("model", ""))
        result = self._load(key)
        return result.get("text", json.dumps(result))

    async def tool_call(
        self,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        response_schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        key = self._hash(system, messages, tools, kwargs.get("model", ""))
        return self._load(key)

    def satisfies_port(self) -> bool:
        from app.domain.agents.ports import LLMClient
        return isinstance(self, LLMClient)


# ---------------------------------------------------------------------------
# build_llm — DI factory (called by container.py)
# ---------------------------------------------------------------------------
def build_llm(
    mode: str = "replay",
    fixtures_dir: Path = Path("tests/fixtures/llm"),
    provider: str = "groq",
    model: str = "llama-3.1-8b-instant",
    api_key: str = "",
    base_url: str = "",
    **kwargs: Any,
) -> Any:
    """
    Build the appropriate LLMClient from config.

    Modes:
      replay  → ReplayClient ($0, offline, default — used by all tests)
      fake    → FakeLLM (unit tests, canned outputs)
      live    → real provider (Groq / Gemini / Ollama — free tier)
      record  → ReplayClient (live + save; not yet wired for Groq)

    Provider routing (live mode only):
      groq       → GroqClient  (OpenAI-compatible, free tier)
      gemini     → (extend here when needed)
      openrouter → (extend here when needed)
      ollama     → GroqClient with local base_url (OpenAI-compatible)
    """
    if mode == "fake":
        return FakeLLM()

    if mode == "live":
        if provider in ("groq", "openrouter", "ollama"):
            # All three use the OpenAI-compatible protocol
            effective_url = base_url or "https://api.groq.com/openai/v1"
            effective_model = model or "llama-3.1-8b-instant"
            if not api_key and provider != "ollama":
                raise ValueError(
                    f"LLM__API_KEY must be set when LLM__PROVIDER={provider}. "
                    "Get a free key at https://console.groq.com"
                )
            logger.info(
                "LLM: live mode — provider=%s model=%s url=%s",
                provider, effective_model, effective_url,
            )
            return GroqClient(
                api_key=api_key,
                model=effective_model,
                base_url=effective_url,
            )
        # Unknown provider — fall back to replay with a warning
        logger.warning(
            "Unknown LLM provider '%s' — falling back to ReplayClient", provider
        )

    # replay / record / unknown → ReplayClient
    return ReplayClient(fixtures_dir=Path(fixtures_dir))
