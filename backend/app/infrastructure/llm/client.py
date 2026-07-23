"""
Infrastructure: Provider-agnostic LLMClient implementations.

Three modes behind the LLMClient port (10-backend.md §8.4):
  replay  — serve saved fixtures keyed by request hash ($0, offline, default)
  record  — live call + save to fixtures (run once to author fixtures)
  live    — real provider call (free-tier; CST-1/CST-3)

Also provides FakeLLM for pure unit tests (canned outputs, no fixtures).

Replay fixture keying:
  A stable SHA-256 hash of (system, messages_json, tools_json, model)
  maps to a saved JSON response in {fixtures_dir}/{prompt_version}/*.json.
  Missing fixture → raises MissingFixtureError (never falls back to live).

Owning docs: 10-backend.md §8.4, 14-prompts.md §12
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class MissingFixtureError(RuntimeError):
    """Raised when replay mode cannot find a fixture for the request hash."""


# ---------------------------------------------------------------------------
# FakeLLM — deterministic canned outputs for unit tests
# ---------------------------------------------------------------------------
class FakeLLM:
    """
    Deterministic LLM stand-in for unit/integration tests.
    Returned outputs are registered by the test; no network, no fixtures.

    Usage:
        fake = FakeLLM()
        fake.set_response(system="...", output={"rationale": "ok", ...})
        result = await fake.tool_call(system, messages, tools)
    """

    def __init__(self) -> None:
        self._responses: list[dict[str, Any]] = []
        self._call_count = 0

    def set_response(self, output: dict[str, Any]) -> None:
        """Queue a response to be returned on the next tool_call."""
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
# ReplayClient — serve saved fixtures (offline, $0, deterministic)
# ---------------------------------------------------------------------------
class ReplayClient:
    """
    Replay LLM: serves saved JSON fixtures keyed by request hash.
    Raises MissingFixtureError on cache miss (never falls back to live).
    This is the DEFAULT mode — all tests and demos use this.
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
        """Save a fixture (called by RecordingClient)."""
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
# build_llm — factory used by the DI container
# ---------------------------------------------------------------------------
def build_llm(
    mode: str = "replay",
    fixtures_dir: Path = Path("tests/fixtures/llm"),
    **kwargs: Any,
) -> Any:
    """
    Build the appropriate LLMClient from config.

    Modes:
      replay  → ReplayClient (default, $0, offline)
      fake    → FakeLLM (unit tests, canned)
      record  → ReplayClient used as base; real provider wraps it (C067+)
      live    → real provider (free-tier; wired in a later commit)
    """
    if mode == "fake":
        return FakeLLM()
    # replay + record + live all use ReplayClient as the fixture store
    return ReplayClient(fixtures_dir=Path(fixtures_dir))
