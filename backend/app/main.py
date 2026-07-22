"""
Agent5G — FastAPI application factory.
C013: minimal app with /health endpoint.
"""
from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Agent5G API",
        description="Agentic AI Service Enablement Platform for 5G Advanced Release 20",
        version="0.1.0",
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness check — returns ok when the server is up."""
        return {"status": "ok"}

    return app


# Module-level app instance used by uvicorn: `uvicorn app.main:app`
app = create_app()
