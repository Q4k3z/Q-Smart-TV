import subprocess
import sys
import os
import pytest
from core.process_manager import process_manager
from core.window_manager import get_process_family_pids, find_visible_window_for_pids

@pytest.mark.asyncio
async def test_process_lifecycle():
    # Start a dummy long-lived process (sleep)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    pid = proc.pid

    process_manager.register_process("test_dummy", pid)
    assert process_manager.is_running("test_dummy") is True
    assert process_manager.get_pid("test_dummy") == pid

    # Test window manager family PIDs
    family = get_process_family_pids(pid)
    assert pid in family

    # Terminate process
    stopped = await process_manager.terminate_process("test_dummy", timeout=2.0)
    assert stopped is True
    assert process_manager.is_running("test_dummy") is False
