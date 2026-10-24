import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from config import settings
from core.event_bus import event_bus
from core.state_manager import state_manager

logger = logging.getLogger("qsmarttv.websocket")

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None)
):
    # Verify auth token
    if not token or token != settings.AUTH_TOKEN:
        logger.warning("Kết nối WebSocket bị từ chối: Token không hợp lệ.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await event_bus.subscribe(websocket)

    # Send current state immediately upon connection
    await websocket.send_json({
        "event": "connected",
        "data": state_manager.get_state()
    })

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await event_bus.unsubscribe(websocket)
    except Exception as e:
        logger.error("Lỗi WebSocket: %s", str(e))
        await event_bus.unsubscribe(websocket)
