import asyncio
import logging
import subprocess
from config import settings
from core.process_manager import process_manager
from core.state_manager import state_manager
from core.window_manager import wait_for_window_by_pid, force_foreground_window, restore_window_by_pid, get_process_family_pids, find_visible_window_for_pids

logger = logging.getLogger('qsmarttv.launcher_service')


class LauncherService:
    def __init__(self):
        self._lock = asyncio.Lock()

    def is_open(self) -> bool:
        return process_manager.is_running('launcher')

    async def open_launcher(self) -> dict:
        async with self._lock:
            if self.is_open():
                pid = process_manager.get_pid('launcher')
                restored = restore_window_by_pid(pid)
                if restored or find_visible_window_for_pids(get_process_family_pids(pid)):
                    changes = {'launcher': 'open'}
                    if restored:
                        changes['active_app'] = 'launcher'
                    await state_manager.update(**changes)
                    return {'status': 'already_running', 'foreground': restored, 'message': 'Launcher đã đang mở.'}
                if not await process_manager.terminate_process('launcher'):
                    return {'status': 'error', 'message': 'Launcher cũ không phản hồi. Không mở thêm cửa sổ.'}
            if not settings.BRAVE_PATH:
                await state_manager.update(launcher='closed')
                return {'status': 'error', 'message': 'Không tìm thấy Brave. Cài từ https://brave.com/download/ hoặc đặt QSMART_BRAVE_PATH trong .env.'}
            profile = settings.DATA_DIR / 'brave-tv-profile'
            url = f'http://127.0.0.1:{settings.PORT}/tv?token={settings.AUTH_TOKEN}'
            cmd = [settings.BRAVE_PATH, f'--user-data-dir={profile}', f'--app={url}',
                   '--start-fullscreen', '--no-first-run', '--no-default-browser-check', '--disable-background-mode']
            await state_manager.update(launcher='starting')
            try:
                proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
                process_manager.register_process('launcher', proc.pid)
                hwnd = await asyncio.to_thread(wait_for_window_by_pid, proc.pid, timeout=8)
                if not hwnd or not self.is_open():
                    await process_manager.terminate_process('launcher')
                    raise RuntimeError('Brave không tạo được cửa sổ TV sau 8 giây.')
                force_foreground_window(hwnd)
                await state_manager.update(launcher='open', active_app='launcher')
                logger.info('Đã xác nhận cửa sổ Launcher PID=%d', proc.pid)
                return {'status': 'success', 'message': 'Đã mở Q Smart TV.'}
            except Exception:
                logger.exception('Không mở được Launcher')
                await state_manager.update(launcher='closed')
                return {'status': 'error', 'message': 'Không mở được cửa sổ Brave. Kiểm tra đường dẫn trình duyệt và data/logs/server.log.'}

    async def exit_launcher(self) -> dict:
        async with self._lock:
            was_open = self.is_open()
            if was_open and not await process_manager.terminate_process('launcher'):
                return {'status': 'error', 'message': 'Không thể đóng launcher. Hãy thử lại.'}
            changes = {'launcher': 'closed'}
            if state_manager.active_app == 'launcher':
                changes['active_app'] = None
            await state_manager.update(**changes)
            return {'status': 'success' if was_open else 'already_closed', 'message': 'Đã đóng Launcher. Server vẫn chạy nền.'}

    async def refresh_state(self):
        async with self._lock:
            if state_manager.launcher != 'open':
                return
            pid = process_manager.get_pid('launcher')
            if pid and find_visible_window_for_pids(get_process_family_pids(pid)):
                return
            if pid and not await process_manager.terminate_process('launcher'):
                return
            changes = {'launcher': 'closed'}
            if state_manager.active_app == 'launcher':
                changes['active_app'] = None
            await state_manager.update(**changes)


launcher_service = LauncherService()
