import asyncio
import uuid
from typing import Literal
from pydantic import BaseModel, Field
from core.input_service import input_service
from core.process_manager import process_manager
from core.state_manager import state_manager
from core.event_bus import event_bus
from core.brave_service import brave_service


class InputCommand(BaseModel):
    action: Literal['key','mouse','input_start','input_update','input_end','release']
    key: str = Field(default='', max_length=32)
    mouse: Literal['move','click','down','up','wheel','release'] = 'move'
    button: Literal['left','right'] = 'left'
    dx: int = Field(default=0, ge=-500, le=500)
    dy: int = Field(default=0, ge=-500, le=500)
    wheel: int = Field(default=0, ge=-1200, le=1200)
    text: str = Field(default='', max_length=8000)
    revision: int = Field(default=1, ge=1, le=1000000)
    start: int = Field(default=0, ge=0, le=16000)
    end: int = Field(default=0, ge=0, le=16000)


class RemoteInput:
    def __init__(self):
        self.sessions = {}
        self.lock = asyncio.Lock()

    def target(self):
        app = state_manager.active_app
        if app == 'launcher':
            return 'launcher'
        if app in ('browser','youtube') and process_manager.is_running('external_browser'):
            return 'external_browser'
        raise RuntimeError('Hãy mở TV hoặc một trang web trước khi dùng chuột/bàn phím.')

    def end(self, owner=None):
        if owner is None:
            self.sessions.clear()
        else:
            self.sessions.pop(owner, None)
        input_service.release_mouse(owner)

    async def _call(self, target, method, *args):
        if target == 'external_browser':
            return await brave_service.input_call(method, *args)
        result = await event_bus.request_tv('input_call', method=method, args=args)
        if not result.get('ok'):
            raise RuntimeError(result.get('message', 'Ô nhập trên TV không phản hồi.'))
        return result.get('result', {})

    async def handle(self, owner, command: InputCommand):
        async with self.lock:
            if command.action in ('input_end','release'):
                self.end(owner)
                return {'status':'success'}
            target = self.target()
            if command.action == 'mouse':
                if command.mouse in ('click','down'):
                    self.end(owner)
                if not input_service.send_mouse(command.mouse,target,owner,command.dx,command.dy,command.wheel,command.button):
                    raise RuntimeError('Chuột chưa nhận được thao tác. Chọn cửa sổ Q Smart TV/Brave TV trên máy tính rồi thử lại.')
                return {'status':'success'}
            if command.action == 'key':
                from core.security import ALLOWED_KEYS
                if command.key not in ALLOWED_KEYS:
                    raise RuntimeError('Phím không được hỗ trợ.')
                self.end(owner)
                from core.app_controller import app_controller
                return await app_controller.press(command.key)
            if command.action == 'input_start':
                self.end(owner)
                if target == 'external_browser' and not input_service._focus_target(target):
                    raise RuntimeError('Không chọn được cửa sổ Brave TV. Hãy chọn nó trên máy tính rồi thử lại.')
                session_id = uuid.uuid4().hex
                await self._call(target, 'start', session_id)
                self.sessions[owner] = {'id':session_id, 'target':target, 'pid':process_manager.get_pid(target), 'revision':0}
                return {'status':'success', 'revision':0}
            session = self.sessions.get(owner)
            if not session or session['target'] != target or session['pid'] != process_manager.get_pid(target):
                self.end(owner)
                raise RuntimeError('Phiên nhập đã kết thúc. Chọn ô nhập và bấm Bắt đầu nhập.')
            revision = command.revision
            if revision == session['revision']:
                return {'status':'success', 'revision':revision}
            if revision != session['revision'] + 1:
                raise RuntimeError('Thứ tự nhập chưa đồng bộ. Bắt đầu phiên nhập mới.')
            length = len(command.text.encode('utf-16-le')) // 2
            if not 0 <= command.start <= command.end <= length:
                raise RuntimeError('Vị trí sửa văn bản không hợp lệ.')
            args = (session['id'], revision, command.text, command.start, command.end)
            try:
                if target == 'launcher':
                    await self._call(target, 'apply', *args)
                else:
                    prepared = await self._call(target, 'prepare', session['id'], revision)
                    if command.text:
                        sent = input_service.send_text(command.text, target)
                    else:
                        sent = not prepared.get('remove') or input_service.send_key('BACKSPACE', target)
                    if not sent:
                        raise RuntimeError('Windows không nhận đủ ký tự. Chọn lại ô nhập rồi bắt đầu lại.')
                    for _ in range(15):
                        result = await self._call(target, 'commit', *args)
                        if not result.get('pending'):
                            break
                        await asyncio.sleep(0.03)
                    else:
                        raise RuntimeError('Ô nhập không nhận đủ văn bản. Bấm Bắt đầu nhập lại.')
                session['revision'] = revision
                return {'status':'success', 'revision':revision}
            except Exception:
                self.end(owner)
                raise


remote_input = RemoteInput()
