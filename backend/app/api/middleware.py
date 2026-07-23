"""
CORS, correlation-id injection, and timing middleware.
Owning docs: 09-api.md §4, §6 (localhost-only CORS)
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach a correlation_id to every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get("X-Correlation-Id", f"req_{uuid.uuid4().hex[:8]}")
        request.state.correlation_id = cid
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[arg-type]
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Correlation-Id"] = cid
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response


def install(app: FastAPI, cors_origin: str = "http://localhost:3000") -> None:
    """Install CORS and correlation-id middleware.

    cors_origin can be a single origin or comma-separated list.
    Use '*' to allow all origins (useful during Railway deployment).
    """
    if cors_origin == "*":
        origins: list[str] = ["*"]
        allow_credentials = False
    else:
        # Support comma-separated list: "https://a.railway.app,http://localhost:3000"
        origins = [o.strip().rstrip("/") for o in cors_origin.split(",") if o.strip()]
        allow_credentials = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https?://.*\.railway\.app",
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationMiddleware)
