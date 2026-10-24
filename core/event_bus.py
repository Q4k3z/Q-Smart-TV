import asyncio
import logging
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger("qsmarttv.event_bus")

class EventBus:
    def __init__(self):
        self._subscribers: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, websocket: WebSocket):
        async with self._lock:
            self._subscribers.add(websocket)
            logger.info("Client WebSocket kết nối. Tổng số kết nối: %d", len(self._subscribers))

    async def unsubscribe(self, websocket: WebSocket):
        async with self._lock:
            self._subscribers.discard(websocket)
            logger.info("Client WebSocket ngắt kết nối. Còn lại: %d", len(self._subscribers))

    async def broadcast(self, message: dict):
        async with self._lock:
            dead_sockets = set()
            for ws in self._subscribers:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                self._subscribers.discard(ws)

event_bus = EventBus()
