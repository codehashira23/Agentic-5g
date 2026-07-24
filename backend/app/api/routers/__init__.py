"""Aggregate all routers into two top-level routers."""
from __future__ import annotations

from fastapi import APIRouter

from .analytics import router as analytics_router
from .health import router as health_router
from .logs import router as logs_router
from .models import router as models_router
from .policies import router as policies_router
from .services import router as services_router
from .settings import router as settings_router
from .simulation import router as simulation_router
from .topology import router as topology_router
from .twin import router as twin_router
from .workflows import router as workflows_router
from .ws import router as ws_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["meta"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(services_router, prefix="/services", tags=["services"])
api_router.include_router(twin_router, prefix="/twin", tags=["twin"])
api_router.include_router(topology_router, prefix="/topology", tags=["topology"])
api_router.include_router(simulation_router, prefix="/simulation", tags=["simulation"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["workflows"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
api_router.include_router(policies_router, prefix="/policies", tags=["policies"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(models_router, prefix="/models", tags=["models"])

__all__ = ["api_router", "ws_router"]
