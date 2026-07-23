"""
Agent5G — FastAPI application factory + lifespan.
Owning docs: 10-backend.md §5
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import errors, middleware
from app.api.routers import api_router, ws_router
from app.infrastructure.config.settings import Settings
from app.infrastructure.container import build_container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Build the DI container, start background tasks, yield, then shutdown."""
    settings: Settings = app.state.settings
    container = await build_container(settings)
    app.state.container = container
    await container.start_background_tasks()
    yield
    await container.stop_background_tasks()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="Agent5G API",
        description=(
            "Agentic AI Service Enablement Platform "
            "for 5G Advanced Release 20"
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.settings = settings or Settings()

    # Middleware (CORS localhost-only, correlation-id, timing)
    middleware.install(app, cors_origin=app.state.settings.cors_origin)

    # Exception handlers → ErrorEnvelope
    errors.install(app)

    # Routes
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ws_router)

    # Health at root (convenience)
    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
