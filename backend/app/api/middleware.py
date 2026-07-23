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
    """Install CORS (localhost-only) and correlation-id middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationMiddleware)
