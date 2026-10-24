import asyncio
import subprocess
import urllib.parse
import logging
from config import settings
from core.security import validate_url
from core.process_manager import process_manager
from core.state_manager import state_manager

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

            cmd = [
                settings.BRAVE_PATH,
                f"--user-data-dir={ext_profile}",
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
                process_manager.register_process("external_browser", proc.pid)
                await state_manager.update(active_app=app_name)
                logger.info("Đã mở website [%s] PID=%d: %s", app_name, proc.pid, valid_url)
                return {"status": "success", "message": f"Đã mở {valid_url}"}
            except Exception as e:
                logger.error("Lỗi khi mở website: %s", str(e))
                return {"status": "error", "message": f"Không thể mở website: {str(e)}"}

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
