"""
Typed application settings loaded from environment variables and .env file.
All secrets use SecretStr — they are never logged or returned by any endpoint.

Usage:
    from app.infrastructure.config import get_settings
    settings = get_settings()
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider configuration.

    Default mode is 'replay' — offline, deterministic, $0 (CST-1/CST-3).
    For live reasoning choose a FREE-TIER provider:
      anthropic  (Claude free credits)
      gemini     (Google AI Studio free tier)
      groq       (Groq free tier)
      openrouter (OpenRouter free models)
      ollama     (fully local, no key, $0)
    """

    mode: Literal["live", "record", "replay"] = "replay"
    provider: Literal["anthropic", "gemini", "groq", "openrouter", "ollama"] = "anthropic"
    model: str = "claude-4.8"
    api_key: SecretStr | None = None      # free-tier key; None for replay / ollama
    base_url: str | None = None           # OpenAI-compatible URL for groq/openrouter/ollama
    fixtures_dir: Path = Path("tests/fixtures/llm")

    model_config = SettingsConfigDict(env_prefix="LLM__", extra="ignore")


class SimSettings(BaseSettings):
    """Digital Twin simulation configuration."""

    default_seed: int = 42
    tick_ms: int = 1000
    default_scenario: str = "baseline_healthy"

    model_config = SettingsConfigDict(env_prefix="SIM__", extra="ignore")


class Settings(BaseSettings):
    """Root application settings.

    Loaded from environment variables and an optional .env file.
    Nested groups use double-underscore as the delimiter:
        LLM__MODE=replay
        SIM__DEFAULT_SEED=7
    """

    env: Literal["dev", "test", "demo", "production"] = "dev"
    db_path: Path = Path("data/agent5g.db")
    cors_origin: str = "http://localhost:3000"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Nested settings — populated from LLM__* and SIM__* env vars
    llm: LLMSettings = LLMSettings()
    sim: SimSettings = SimSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @property
    def effective_db_path(self) -> Path:
        """On Railway (production), use /tmp which is always writable."""
        if self.env == "production":
            return Path("/tmp/agent5g.db")
        return self.db_path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once at startup)."""
    return Settings()
