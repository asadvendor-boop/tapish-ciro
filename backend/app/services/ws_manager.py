"""
WebSocket connection manager — broadcasts events to trace, alerts, and map channels.
"""

import json
from typing import Dict, List, Set

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections across multiple channels."""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {
            "trace": set(),
            "alerts": set(),
            "map": set(),
        }

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        self._connections.get(channel, set()).discard(websocket)

    def active_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    async def broadcast(self, channel: str, data: dict):
        """Broadcast a JSON message to all connections on a channel."""
        if channel not in self._connections:
            return
        dead = []
        message = json.dumps(data, default=str)
        # Iterate over a snapshot to avoid RuntimeError if disconnect()
        # modifies the set while we're awaiting send_text()
        for ws in list(self._connections[channel]):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[channel].discard(ws)

    async def broadcast_trace(self, trace_event: dict):
        """Broadcast an agent trace event to the trace channel."""
        await self.broadcast("trace", trace_event)

    async def broadcast_alert(self, alert: dict):
        """Broadcast a citizen alert to the alerts channel."""
        await self.broadcast("alerts", alert)

    async def broadcast_map(self, map_update: dict):
        """Broadcast a map update (resource movement, crisis state)."""
        await self.broadcast("map", map_update)
