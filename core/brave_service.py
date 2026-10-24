import asyncio
import subprocess
import urllib.parse
import logging
from config import settings
from core.security import validate_url
from core.process_manager import process_manager
from core.state_manager import state_manager
from core.window_manager import (
    wait_for_window_by_pid,
    force_foreground_window,
    minimize_window_by_pid,
    get_process_family_pids,
    find_visible_window_for_pids
)

logger = logging.getLogger("qsmarttv.brave_service")

class BraveService:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def open_url(self, url: str, app_name: str = "browser") -> dict:
        async with self._lock:
            valid_url = validate_url(url)
            if not settings.BRAVE_PATH:
                return {"status": "error", "message": "Không tìm thấy Brave Browser."}

            ext_profile = settings.DATA_DIR / "brave-external-profile"
            ext_profile.mkdir(parents=True, exist_ok=True)

            # Check if external browser process is already running
            existing_pid = process_manager.get_pid("external_browser")

            cmd = [
                settings.BRAVE_PATH,
                f"--user-data-dir={ext_profile}",
                "--new-window",
                "--start-fullscreen",
                "--no-first-run",
                "--no-default-browser-check",
                valid_url
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True
                )
                target_pid = proc.pid

                if not existing_pid:
                    process_manager.register_process("external_browser", proc.pid)
                else:
                    target_pid = existing_pid

                await state_manager.update(active_app=app_name)
                logger.info("Đã mở website [%s] target_pid=%d: %s", app_name, target_pid, valid_url)

                # 3. Schedule async foreground activation to ensure window appears on top
                asyncio.create_task(self._ensure_browser_foreground(target_pid, proc.pid))

                return {"status": "success", "message": f"Đã mở {valid_url}"}
            except Exception as e:
                logger.error("Lỗi khi mở website: %s", str(e))
                return {"status": "error", "message": f"Không thể mở website: {str(e)}"}

    async def _ensure_browser_foreground(self, target_pid: int, spawned_pid: int):
        """Asynchronously waits for the browser window to appear and forces it to the foreground."""
        await asyncio.sleep(0.3)
        # Try both target_pid and spawned_pid
        for _ in range(12):
            pids = get_process_family_pids(target_pid)
            if spawned_pid and spawned_pid != target_pid:
                pids.extend(get_process_family_pids(spawned_pid))

            hwnd = find_visible_window_for_pids(pids)
            if hwnd:
                force_foreground_window(hwnd)
                logger.info("Đã kéo cửa sổ trình duyệt lên đầu màn hình thành công (HWND=%s)", hwnd)
                return
            await asyncio.sleep(0.25)
        logger.warning("Không tìm thấy cửa sổ trình duyệt sau khi khởi chạy để đưa lên đầu.")

    async def open_youtube(self, search_query: str = "") -> dict:
        if search_query and search_query.strip():
            encoded = urllib.parse.quote_plus(search_query.strip())
            url = f"https://www.youtube.com/results?search_query={encoded}"
        else:
            url = "https://www.youtube.com"
        return await self.open_url(url, app_name="youtube")

    async def close_external_browser(self) -> bool:
        return await process_manager.terminate_process("external_browser")

brave_service = BraveService()
