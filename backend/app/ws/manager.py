import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"type": event_type, "payload": payload})
        async with self._lock:
            dead: list[WebSocket] = []
            for connection in self._connections:
                try:
                    await connection.send_text(message)
                except Exception:
                    dead.append(connection)
            for connection in dead:
                self._connections.discard(connection)


ws_manager = ConnectionManager()
