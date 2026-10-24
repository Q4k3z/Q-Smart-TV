import asyncio
import logging
import psutil
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger("qsmarttv.process_manager")

class ProcessManager:
    def __init__(self):
        self._processes: Dict[str, psutil.Process] = {}
        self._lock = asyncio.Lock()

    def adopt_browser_profile(self, name: str, executable: str, profile: Path):
        """Recover only a browser root with our exact executable and private profile."""
        if not executable or self.is_running(name):
            return
        expected_exe = str(Path(executable).resolve()).casefold()
        expected_arg = f'--user-data-dir={profile}'.casefold()
        for proc in psutil.process_iter(['exe', 'cmdline']):
            try:
                args = proc.info['cmdline'] or []
                if (proc.info['exe'] and str(Path(proc.info['exe']).resolve()).casefold() == expected_exe
                        and expected_arg in [arg.casefold() for arg in args]
                        and not any(arg.startswith('--type=') for arg in args)):
                    self.register_process(name, proc.pid)
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def register_process(self, name: str, pid: int):
        try:
            p = psutil.Process(pid)
            self._processes[name] = p
            logger.info("Đã đăng ký tiến trình [%s] PID=%d", name, pid)
        except psutil.NoSuchProcess:
            logger.error("Không tìm thấy tiến trình PID=%d để đăng ký cho [%s]", pid, name)

    def is_running(self, name: str) -> bool:
        proc = self._processes.get(name)
        if not proc:
            return False
        try:
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self._processes.pop(name, None)
            return False

    def get_pid(self, name: str) -> Optional[int]:
        if self.is_running(name):
            return self._processes[name].pid
        return None

    async def terminate_process(self, name: str, timeout: float = 3.0) -> bool:
        """Terminates a managed process and its children gracefully, falling back to kill if needed."""
        async with self._lock:
            proc = self._processes.get(name)
            if not proc:
                return True
            try:
                if not proc.is_running():
                    self._processes.pop(name, None)
                    return True
                
                # Terminate children first
                children = proc.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                proc.terminate()

                # Wait for termination
                gone, alive = await asyncio.to_thread(psutil.wait_procs, children + [proc], timeout=timeout)
                if alive:
                    logger.warning("Tiến trình [%s] không dừng sau %s giây, tiến hành kill", name, timeout)
                    for p in alive:
                        try:
                            p.kill()
                        except psutil.NoSuchProcess:
                            pass
                    _, alive = await asyncio.to_thread(psutil.wait_procs, alive, timeout=timeout)
                    if alive:
                        return False
                self._processes.pop(name, None)
                logger.info("Đã đóng tiến trình [%s]", name)
                return True
            except psutil.NoSuchProcess:
                self._processes.pop(name, None)
                return True
            except Exception as e:
                logger.error("Lỗi khi đóng tiến trình [%s]: %s", name, str(e))
                return False

process_manager = ProcessManager()
