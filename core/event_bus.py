import asyncio
import logging
import uuid
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger("qsmarttv.event_bus")

class EventBus:
    def __init__(self):
        self._subscribers: Set[WebSocket] = set()
        self._tv_subscribers: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._requests = {}

    async def subscribe(self, websocket: WebSocket, role: str = "remote"):
        async with self._lock:
            self._subscribers.add(websocket)
            if role == "tv":
                self._tv_subscribers.add(websocket)
            logger.info("Client WebSocket kết nối. Tổng số kết nối: %d", len(self._subscribers))

    async def unsubscribe(self, websocket: WebSocket):
        async with self._lock:
            self._subscribers.discard(websocket)
            self._tv_subscribers.discard(websocket)
            logger.info("Client WebSocket ngắt kết nối. Còn lại: %d", len(self._subscribers))

    async def broadcast(self, message: dict):
        async with self._lock:
            dead_sockets = set()
            for ws in self._subscribers:
                try:
                    await asyncio.wait_for(ws.send_json(message), timeout=2)
                except Exception:
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                self._subscribers.discard(ws)
                self._tv_subscribers.discard(ws)

    async def send_tv(self, action: str, **data) -> bool:
        delivered = False
        for ws in tuple(self._tv_subscribers):
            try:
                await asyncio.wait_for(ws.send_json({"event": "control", "data": {"action": action, **data}}), 2)
                delivered = True
            except Exception:
                await self.unsubscribe(ws)
        return delivered

    async def request_tv(self, action, **data):
        if len(self._tv_subscribers) != 1:
            raise RuntimeError('Cần đúng một giao diện TV để nhập trực tiếp. Đóng các tab TV phụ rồi thử lại.')
        request_id = uuid.uuid4().hex
        socket = next(iter(self._tv_subscribers))
        future = asyncio.get_running_loop().create_future()
        self._requests[request_id] = (socket, future)
        try:
            await socket.send_json({'event':'control', 'data':{'action':action,'request_id':request_id,**data}})
            return await asyncio.wait_for(future, 3)
        finally:
            self._requests.pop(request_id, None)

    def resolve_tv(self, socket, request_id, result):
        entry = self._requests.get(request_id)
        if entry and entry[0] is socket and not entry[1].done():
            entry[1].set_result(result)

event_bus = EventBus()
