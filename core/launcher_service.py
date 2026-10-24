import asyncio
import subprocess
import logging
import ctypes
from config import settings
from core.process_manager import process_manager
from core.state_manager import state_manager

logger = logging.getLogger("qsmarttv.launcher_service")

def bring_window_to_front(pid: int):
    """Brings the window belonging to the given PID to the foreground."""
    user32 = ctypes.windll.user32
    def enum_cb(hwnd, lparam):
        w_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
        if w_pid.value == pid and user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return False
        return True

    cb_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    try:
        user32.EnumWindows(cb_type(enum_cb), 0)
    except Exception as e:
        logger.debug("Không thể đưa cửa sổ PID=%d lên foreground: %s", pid, str(e))

class LauncherService:
    def __init__(self):
        self._lock = asyncio.Lock()

    def is_open(self) -> bool:
        return process_manager.is_running("launcher")

    async def open_launcher(self) -> dict:
        async with self._lock:
            if self.is_open():
                pid = process_manager.get_pid("launcher")
                if pid:
                    bring_window_to_front(pid)
                logger.info("Launcher đã đang chạy. Đã đưa cửa sổ lên foreground.")
                return {"status": "already_running", "message": "Launcher đã đang mở trên màn hình."}

            if not settings.BRAVE_PATH:
                err_msg = "Không tìm thấy Brave Browser. Vui lòng cài đặt Brave hoặc cấu hình đường dẫn trong file .env."
                logger.error(err_msg)
                return {"status": "error", "message": err_msg}

            tv_profile = settings.DATA_DIR / "brave-tv-profile"
            tv_profile.mkdir(parents=True, exist_ok=True)
            launcher_url = f"http://127.0.0.1:{settings.PORT}/tv?token={settings.AUTH_TOKEN}"

            cmd = [
                settings.BRAVE_PATH,
                f"--user-data-dir={tv_profile}",
                f"--app={launcher_url}",
                "--start-fullscreen",
                "--no-first-run",
                "--no-default-browser-check"
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True
                )
                process_manager.register_process("launcher", proc.pid)
                await state_manager.update(launcher="open", active_app="launcher")
                logger.info("Đã mở Q Smart TV Launcher PID=%d", proc.pid)
                return {"status": "success", "message": "Đã mở giao diện Launcher thành công."}
            except Exception as e:
                logger.error("Lỗi khi khởi chạy Launcher: %s", str(e))
                return {"status": "error", "message": f"Lỗi khởi chạy launcher: {str(e)}"}

    async def exit_launcher(self) -> dict:
        async with self._lock:
            if not self.is_open():
                await state_manager.update(launcher="closed")
                return {"status": "already_closed", "message": "Launcher đã ở trạng thái đóng."}

            success = await process_manager.terminate_process("launcher")
            await state_manager.update(launcher="closed")
            if success:
                logger.info("Đã đóng Launcher theo yêu cầu từ Remote.")
                return {"status": "success", "message": "Đã đóng Launcher. Server vẫn chạy nền."}
            else:
                return {"status": "error", "message": "Không thể đóng tiến trình launcher."}

launcher_service = LauncherService()
