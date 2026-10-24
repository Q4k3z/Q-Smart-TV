import logging
import secrets
import asyncio
import json
import uuid
from pydantic import ValidationError
from core.remote_input import remote_input, InputCommand
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from config import settings
from core.event_bus import event_bus
from core.state_manager import state_manager

logger = logging.getLogger("qsmarttv.websocket")

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
    role: str = Query("remote")
):
    # Verify auth token
    if not token or not secrets.compare_digest(token, settings.AUTH_TOKEN):
        logger.warning("Kết nối WebSocket bị từ chối: Token không hợp lệ.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if role not in ("remote", "tv") or (role == "tv" and websocket.client.host not in ("127.0.0.1", "::1")):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    owner = uuid.uuid4().hex
    await event_bus.subscribe(websocket, role)

    # Send current state immediately upon connection
    await websocket.send_json({
        "event": "connected",
        "data": state_manager.get_state()
    })

    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=20 if role == 'remote' else 90)
            if data == "ping":
                await websocket.send_text("pong")
                continue
            if len(data) > 50000:
                await websocket.close(code=1009)
                return
            request_id = None
            try:
                message = json.loads(data)
                if not isinstance(message, dict):
                    raise ValueError()
                if role == 'tv':
                    if message.get('event') == 'control_result':
                        event_bus.resolve_tv(websocket, message.get('request_id'), message.get('result', {}))
                    continue
                request_id = message.get('id')
                if not isinstance(request_id, int) or not 0 <= request_id <= 2**31:
                    raise ValueError()
                result = await remote_input.handle(owner, InputCommand.model_validate(message))
            except (ValueError, ValidationError):
                result = {'status':'error', 'message':'Thao tác không hợp lệ.'}
            except Exception as error:
                result = {'status':'error', 'message':getattr(error, 'detail', str(error)) or 'Không gửi được thao tác. Hãy thử lại.'}
            await websocket.send_json({'event':'input_result','id':request_id,'data':result})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Lỗi WebSocket: %s", str(e))
    finally:
        remote_input.end(owner)
        await event_bus.unsubscribe(websocket)
