from fastapi import HTTPException
from core.launcher_service import launcher_service
from core.mpv_service import mpv_service
from core.input_service import input_service
from core.state_manager import state_manager
from core.process_manager import process_manager
from core.event_bus import event_bus
from core.brave_service import brave_service


class AppController:
    async def handle_home(self) -> dict:
        from core.remote_input import remote_input
        remote_input.end()
        if not await brave_service.close_external_browser():
            return {'status':'error', 'message':'Không đóng được web TV. Vui lòng thử lại.'}
        if mpv_service.is_running():
            result = await mpv_service.stop()
            if result.get('status') == 'error':
                return result
        result = await launcher_service.open_launcher()
        if result['status'] == 'error':
            return result
        await state_manager.update(active_app='launcher')
        await event_bus.send_tv('home')
        return {'status': 'success', 'action': 'home'}

    async def handle_back(self) -> dict:
        from core.remote_input import remote_input
        remote_input.end()
        if state_manager.active_app in ('youtube', 'browser') and process_manager.is_running('external_browser'):
            try:
                if not await brave_service.back():
                    return await self.handle_home()
            except Exception:
                raise HTTPException(409, 'Không quay lại được trang trước. Thử nút Về TV.')
        elif state_manager.active_app in ('movies', 'iptv') and mpv_service.is_running():
            return {'status': 'success', 'action': 'back', 'message': 'Media vẫn đang phát. Dùng Home để về TV hoặc Stop để dừng.'}
        elif not await event_bus.send_tv('back'):
            raise HTTPException(409, 'Giao diện TV chưa kết nối. Hãy mở lại TV.')
        return {'status': 'success', 'action': 'back'}

    async def press(self, key: str) -> dict:
        if state_manager.active_app == 'launcher':
            if not await event_bus.send_tv('key', key=key):
                raise HTTPException(409, 'Giao diện TV chưa kết nối. Hãy mở lại TV.')
        else:
            target = 'mpv' if mpv_service.is_running() else 'external_browser'
            if not input_service.send_key(key, target=target):
                raise HTTPException(409, 'Không có cửa sổ TV phù hợp để nhận phím.')
        return {'status': 'success', 'key': key}

    async def text(self, text: str) -> dict:
        if state_manager.active_app == 'launcher':
            if not await event_bus.send_tv('text', text=text):
                raise HTTPException(409, 'Giao diện TV chưa kết nối.')
        elif state_manager.active_app in ('browser', 'youtube'):
            if not input_service.send_text(text, target='external_browser'):
                raise HTTPException(409, 'Không gửi được văn bản. Hãy chọn ô nhập trên trình duyệt TV.')
        else:
            raise HTTPException(409, 'Ứng dụng hiện tại không hỗ trợ nhập văn bản.')
        return {'status': 'success', 'length': len(text)}

    async def exit_tv(self) -> dict:
        from core.remote_input import remote_input
        remote_input.end()
        return await launcher_service.exit_launcher()

    async def reopen_tv(self) -> dict:
        return await launcher_service.open_launcher()


app_controller = AppController()
