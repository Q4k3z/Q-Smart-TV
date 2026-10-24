import ctypes
import ctypes.wintypes
import time
import logging
from typing import List, Optional
import psutil

logger = logging.getLogger("qsmarttv.window_manager")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# HWND is pointer-sized on 64-bit Windows; ctypes defaults to a 32-bit int.
user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
for _name in ("IsWindow", "IsWindowVisible", "IsIconic", "SetForegroundWindow", "BringWindowToTop"):
    getattr(user32, _name).argtypes = [ctypes.wintypes.HWND]
user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
user32.GetWindowRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
user32.GetWindow.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.UINT]
user32.GetWindow.restype = ctypes.wintypes.HWND
user32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t

SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_SHOWMINNOACTIVE = 7
SW_SHOWNA = 8
SW_RESTORE = 9

def get_process_family_pids(root_pid: int) -> List[int]:
    """Returns the root PID and all its descendant PIDs."""
    pids = [root_pid]
    try:
        p = psutil.Process(root_pid)
        for child in p.children(recursive=True):
            pids.append(child.pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return pids

def find_visible_window_for_pids(pids: List[int]) -> Optional[int]:
    """Finds the first visible or iconic top-level window belonging to any of the specified PIDs."""
    pids_set = set(pids)
    found_hwnd: Optional[int] = None
    candidates = []

    def enum_cb(hwnd, lparam):
        nonlocal found_hwnd
        w_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
        if w_pid.value in pids_set:
            is_vis = user32.IsWindowVisible(hwnd)
            is_icon = user32.IsIconic(hwnd)
            if is_vis or is_icon:
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                if is_icon or (width > 50 and height > 50):
                    # Browser bubbles/dialogs share the same PID. Prefer an
                    # unowned, resizable main window instead of the first HWND.
                    style = user32.GetWindowLongPtrW(hwnd, -16)
                    score = (not bool(user32.GetWindow(hwnd, 4)), bool(style & 0x00040000), width * height)
                    candidates.append((score, hwnd))
        return True

    cb_type = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(cb_type(enum_cb), 0)
    if not candidates:
        try:
            hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
            if hdesk:
                user32.EnumDesktopWindows(hdesk, cb_type(enum_cb), 0)
                user32.CloseDesktop(hdesk)
        except Exception:
            pass
    return max(candidates, key=lambda item: item[0])[1] if candidates else None

def wait_for_window_by_pid(root_pid: int, timeout: float = 3.5) -> Optional[int]:
    """Polls until a visible top-level window appears for the given PID or its child processes."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        pids = get_process_family_pids(root_pid)
        hwnd = find_visible_window_for_pids(pids)
        if hwnd:
            return hwnd
        time.sleep(0.15)
    return None

def force_foreground_window(hwnd: int) -> bool:
    """Forces the specified window to the foreground, bypassing Windows Foreground Lock."""
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)

        foreground_hwnd = user32.GetForegroundWindow()
        curr_thread = kernel32.GetCurrentThreadId()
        fore_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)

        if fore_thread != curr_thread and fore_thread != 0:
            user32.AttachThreadInput(curr_thread, fore_thread, True)
        if target_thread != curr_thread and target_thread != 0:
            user32.AttachThreadInput(curr_thread, target_thread, True)

        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)

        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)

        if fore_thread != curr_thread and fore_thread != 0:
            user32.AttachThreadInput(curr_thread, fore_thread, False)
        if target_thread != curr_thread and target_thread != 0:
            user32.AttachThreadInput(curr_thread, target_thread, False)

        logger.info("Đã đưa cửa sổ HWND=%s lên Foreground thành công.", hwnd)
        return user32.GetForegroundWindow() == hwnd
    except Exception as e:
        logger.error("Lỗi khi đưa cửa sổ lên Foreground: %s", str(e))
        return False

def minimize_window_by_pid(root_pid: int) -> bool:
    """Minimizes the window of the specified process."""
    try:
        pids = get_process_family_pids(root_pid)
        hwnd = find_visible_window_for_pids(pids)
        if hwnd:
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            logger.info("Đã thu nhỏ (minimize) cửa sổ PID=%d HWND=%s", root_pid, hwnd)
            return True
    except Exception as e:
        logger.debug("Không thể thu nhỏ cửa sổ PID=%d: %s", root_pid, str(e))
    return False

def restore_window_by_pid(root_pid: int) -> bool:
    """Restores and focuses the window of the specified process."""
    try:
        pids = get_process_family_pids(root_pid)
        hwnd = find_visible_window_for_pids(pids)
        if hwnd:
            return force_foreground_window(hwnd)
    except Exception as e:
        logger.debug("Không thể khôi phục cửa sổ PID=%d: %s", root_pid, str(e))
    return False
