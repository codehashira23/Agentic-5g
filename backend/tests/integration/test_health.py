"""
C014: Integration test for the /health endpoint.
Uses httpx.AsyncClient against the real FastAPI app (no network).
"""
import pytest
from app.main import create_app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:  # type: ignore[misc]
    """Provide an async test client for the app."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_health_returns_ok(client: AsyncClient) -> None:
    """GET /health must return 200 with {"status": "ok"}."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_health_content_type_is_json(client: AsyncClient) -> None:
    """GET /health must return application/json."""
    response = await client.get("/health")
    assert "application/json" in response.headers["content-type"]
