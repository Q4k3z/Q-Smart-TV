import asyncio
import json
import logging
import subprocess
import time
from typing import Optional, Dict, Any
from config import settings
from core.process_manager import process_manager
from core.state_manager import state_manager
from core.window_manager import restore_window_by_pid

logger = logging.getLogger("qsmarttv.mpv_service")

class MPVService:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._monitor_task: Optional[asyncio.Task] = None
        self._pipe_name = settings.MPV_PIPE_NAME

    def is_running(self) -> bool:
        return process_manager.is_running("mpv")

    def _send_ipc(self, command: list, timeout: float = 1.0) -> Optional[dict]:
        """Sends a JSON IPC command to mpv over the Windows named pipe."""
        if not self.is_running():
            return None
        payload = json.dumps({"command": command}) + "\n"
        for _ in range(3):
            try:
                with open(self._pipe_name, "r+b", buffering=0) as pipe:
                    pipe.write(payload.encode("utf-8"))
                    line = pipe.readline().decode("utf-8").strip()
                    if line:
                        return json.loads(line)
            except Exception as e:
                time.sleep(0.1)
        return None

    async def play(self, target: str, title: str = "", is_stream: bool = False) -> dict:
        async with self._lock:
            # Stop existing playback if any
            await self._stop_internal()

            if not settings.MPV_PATH:
                err_msg = "Không tìm thấy mpv player. Vui lòng cài đặt mpv hoặc cấu hình trong file .env."
                logger.error(err_msg)
                await state_manager.update(mpv="error")
                return {"status": "error", "message": err_msg}

            display_title = title if title else "Q Smart TV Media"
            cmd = [
                settings.MPV_PATH,
                f"--input-ipc-server={self._pipe_name}",
                "--fs",
                "--ontop",
                "--force-window=immediate",
                f"--title={display_title}",
                "--idle=no",
                "--keep-open=no",
                target
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True
                )
                process_manager.register_process("mpv", proc.pid)
                app_type = "iptv" if is_stream else "movies"
                await state_manager.update(
                    mpv="playing",
                    active_app=app_type,
                    current_media={"title": display_title, "target": target, "is_stream": is_stream}
                )

                if self._monitor_task and not self._monitor_task.done():
                    self._monitor_task.cancel()
                self._monitor_task = asyncio.create_task(self._monitor_lifecycle(proc.pid))

                logger.info("Đã khởi chạy phát media bằng mpv PID=%d: %s", proc.pid, display_title)
                return {"status": "success", "message": f"Đang phát: {display_title}"}
            except Exception as e:
                logger.error("Lỗi khi chạy mpv: %s", str(e))
                await state_manager.update(mpv="error")
                return {"status": "error", "message": f"Lỗi khởi chạy mpv: {str(e)}"}

    async def _monitor_lifecycle(self, pid: int):
        """Monitors mpv process and updates state when mpv exits."""
        try:
            while process_manager.is_running("mpv") and process_manager.get_pid("mpv") == pid:
                await asyncio.sleep(0.8)
        except asyncio.CancelledError:
            return
        finally:
            if not process_manager.is_running("mpv"):
                logger.info("Tiến trình mpv PID=%d đã kết thúc.", pid)
                await state_manager.update(mpv="stopped", current_media=None)
                # Restore launcher window to foreground
                launcher_pid = process_manager.get_pid("launcher")
                if launcher_pid:
                    restore_window_by_pid(launcher_pid)

    async def pause_toggle(self) -> dict:
        if not self.is_running():
            return {"status": "error", "message": "mpv không đang phát."}
        self._send_ipc(["cycle", "pause"])
        current_mpv_state = state_manager.mpv
        new_state = "paused" if current_mpv_state == "playing" else "playing"
        await state_manager.update(mpv=new_state)
        return {"status": "success", "state": new_state}

    async def seek(self, seconds: float) -> dict:
        if not self.is_running():
            return {"status": "error", "message": "mpv không đang phát."}
        self._send_ipc(["seek", seconds, "relative"])
        return {"status": "success", "seek": seconds}

    async def volume_change(self, delta: int) -> dict:
        if not self.is_running():
            return {"status": "error", "message": "mpv không đang phát."}
        self._send_ipc(["add", "volume", delta])
        return {"status": "success", "volume_delta": delta}

    async def _stop_internal(self):
        if self.is_running():
            self._send_ipc(["quit"])
            await process_manager.terminate_process("mpv", timeout=2.0)
        await state_manager.update(mpv="stopped", current_media=None)

    async def stop(self) -> dict:
        async with self._lock:
            await self._stop_internal()
            launcher_pid = process_manager.get_pid("launcher")
            if launcher_pid:
                restore_window_by_pid(launcher_pid)
            return {"status": "success", "message": "Đã dừng phát media."}

mpv_service = MPVService()
