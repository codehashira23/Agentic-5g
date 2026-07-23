"""WebSocket endpoint."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.ws.hub import WebSocketHub

router = APIRouter()

# Module-level hub shared across all connections
_hub = WebSocketHub()


def get_hub() -> WebSocketHub:
    return _hub


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await _hub.connect(ws)
    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                # Handle subscription filter messages (09-api.md §10)
                try:
                    msg = json.loads(data)
                    if msg.get("op") == "ping":
                        await ws.send_text('{"type":"PONG"}')
                except Exception:
                    pass
            except TimeoutError:
                # Send keepalive PING
                try:
                    await ws.send_text('{"type":"PING"}')
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        _hub.disconnect(ws)
