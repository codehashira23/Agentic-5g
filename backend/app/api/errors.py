"""
Centralized exception handlers → ErrorEnvelope.
Maps typed domain exceptions to HTTP status codes (09-api.md §5).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.schemas.common import ErrorEnvelope


def _envelope(status: int, title: str, detail: str = "",
              error_type: str = "generic",
              correlation_id: str | None = None,
              errors: list | None = None) -> JSONResponse:
    body = ErrorEnvelope(
        type=f"https://agent5g.local/errors/{error_type}",
        title=title,
        status=status,
        detail=detail,
        correlation_id=correlation_id,
        errors=errors or [],
    )
    return JSONResponse(status_code=status, content=body.model_dump())


def install(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def _validation(request: Request, exc: ValidationError) -> JSONResponse:
        cid = getattr(request.state, "correlation_id", None)
        errs = [
            {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _envelope(422, "Validation failed", str(exc),
                         "validation", cid, errs)

    @app.exception_handler(KeyError)
    async def _not_found(request: Request, exc: KeyError) -> JSONResponse:
        cid = getattr(request.state, "correlation_id", None)
        return _envelope(404, "Not found", str(exc), "not-found", cid)

    @app.exception_handler(ValueError)
    async def _value(request: Request, exc: ValueError) -> JSONResponse:
        cid = getattr(request.state, "correlation_id", None)
        msg = str(exc)
        if "PLC-" in msg or "policy" in msg.lower():
            return _envelope(423, "Policy blocked", msg, "policy-blocked", cid)
        return _envelope(422, "Bad request", msg, "bad-request", cid)

    @app.exception_handler(Exception)
    async def _generic(request: Request, exc: Exception) -> JSONResponse:
        cid = getattr(request.state, "correlation_id", None)
        return _envelope(500, "Internal server error",
                         "An unexpected error occurred.",
                         "internal", cid)
