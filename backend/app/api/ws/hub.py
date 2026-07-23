"""
WebSocket hub — manages connections and fans out events.
Owning docs: 09-api.md §10
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class WebSocketHub:
    """
    Manages connected WebSocket clients.
    Subscribed to the event bus; fans events out to all connected clients.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        # Send HELLO handshake
        await self._send_one(ws, {
            "type": "HELLO",
            "server_version": "0.1.0",
            "api": "v1",
            "schema_version": "1",
            "ts": datetime.now(UTC).isoformat(),
        })

    def disconnect(self, ws: WebSocket) -> None:
        self._connections = [c for c in self._connections if c is not ws]

    async def broadcast(self, event: Any) -> None:
        """Broadcast a domain event to all connected clients."""
        evt_type = getattr(event, "type", None)
        if evt_type and hasattr(evt_type, "value"):
            evt_type = evt_type.value

        payload: dict[str, Any] = {}
        if hasattr(event, "model_dump"):
            raw = event.model_dump()
            payload = {k: v for k, v in raw.items()
                       if k not in ("type", "event_id", "correlation_id", "ts", "tick")}
        elif isinstance(event, dict):
            payload = event

        envelope = {
            "type": evt_type or "UNKNOWN",
            "event_id": getattr(event, "event_id", ""),
            "correlation_id": getattr(event, "correlation_id", None),
            "ts": getattr(event, "ts", datetime.now(UTC)).isoformat()
                  if not isinstance(getattr(event, "ts", None), str)
                  else getattr(event, "ts", ""),
            "tick": getattr(event, "tick", 0),
            "payload": payload,
        }
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(json.dumps(envelope, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _send_one(self, ws: WebSocket, data: dict[str, Any]) -> None:
        try:
            await ws.send_text(json.dumps(data, default=str))
        except Exception:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
