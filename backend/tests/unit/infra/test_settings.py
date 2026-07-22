"""
C015: Unit tests for typed Settings.
Verifies defaults, secret masking, and nested env loading.
"""

import pytest
from app.infrastructure.config.settings import Settings


class TestDefaultSettings:
    """Settings load with correct defaults when no .env is present."""

    def test_default_env_is_dev(self) -> None:
        s = Settings()
        assert s.env == "dev"

    def test_default_llm_mode_is_replay(self) -> None:
        s = Settings()
        assert s.llm.mode == "replay"

    def test_default_llm_model(self) -> None:
        s = Settings()
        assert s.llm.model == "claude-4.8"

    def test_default_llm_api_key_is_none(self) -> None:
        """API key must default to None — never hard-coded."""
        s = Settings()
        assert s.llm.api_key is None

    def test_default_sim_seed(self) -> None:
        s = Settings()
        assert s.sim.default_seed == 42

    def test_default_sim_tick_ms(self) -> None:
        s = Settings()
        assert s.sim.tick_ms == 1000

    def test_default_cors_origin(self) -> None:
        s = Settings()
        assert s.cors_origin == "http://localhost:3000"

    def test_db_path_is_path_object(self) -> None:
        from pathlib import Path

        s = Settings()
        assert isinstance(s.db_path, Path)


class TestSecretHandling:
    """API key is SecretStr — its value is never exposed as plain text."""

    def test_api_key_is_secret_str_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pydantic import SecretStr

        monkeypatch.setenv("LLM__API_KEY", "test-key-123")
        s = Settings()
        assert isinstance(s.llm.api_key, SecretStr)

    def test_api_key_repr_does_not_expose_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM__API_KEY", "super-secret")
        s = Settings()
        assert s.llm.api_key is not None
        # The string representation must NOT contain the real value
        assert "super-secret" not in repr(s.llm.api_key)
        assert "super-secret" not in str(s.llm.api_key)


class TestEnvOverrides:
    """Settings can be overridden via environment variables."""

    def test_llm_mode_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM__MODE", "live")
        s = Settings()
        assert s.llm.mode == "live"

    def test_sim_seed_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SIM__DEFAULT_SEED", "7")
        s = Settings()
        assert s.sim.default_seed == 7

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENV", "demo")
        s = Settings()
        assert s.env == "demo"
