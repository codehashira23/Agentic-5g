"""
Dependency-injection providers for FastAPI routes.
All adapters come from the Container; nothing else constructs them.
"""
from __future__ import annotations

from fastapi import Request

from app.infrastructure.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container  # type: ignore[no-any-return]
