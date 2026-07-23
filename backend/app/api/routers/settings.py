"""Settings router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.infrastructure.container import Container

router = APIRouter()


@router.get("")
async def get_settings(c: Container = Depends(get_container)) -> dict[str, Any]:
    from app.infrastructure.config.settings import Settings
    cfg = Settings()
    return {
        "llm": {
            "mode": cfg.llm.mode,
            "model": cfg.llm.model,
            "key_set": cfg.llm.api_key is not None,  # never return the key value
        },
        "simulation": {
            "default_seed": cfg.sim.default_seed,
            "tick_ms": cfg.sim.tick_ms,
            "default_scenario": cfg.sim.default_scenario,
        },
        "env": cfg.env,
    }


@router.put("")
async def update_settings(body: dict[str, Any]) -> dict[str, Any]:
    # In-process settings update is env-var driven; acknowledge but note restart
    return {"ok": True, "restart_required": True,
            "message": "Settings are loaded from .env; restart to apply."}
