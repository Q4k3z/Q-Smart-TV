import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger('qsmarttv.input_service')
VK_CODES = {'UP':0x26,'DOWN':0x28,'LEFT':0x25,'RIGHT':0x27,'ENTER':0x0D,'ESCAPE':0x1B,
    'BACKSPACE':0x08,'DELETE':0x2E,'HOME':0x24,'END':0x23,'TAB':0x09,'SPACE':0x20,
    'PAGE_UP':0x21,'PAGE_DOWN':0x22,'A':0x41,'Z':0x5A,'VOLUME_UP':0xAF,'VOLUME_DOWN':0xAE,
    'MUTE':0xAD,'PLAY_PAUSE':0xB3}
MODIFIERS = {'SHIFT':0x10,'CTRL':0x11,'ALT':0x12}
KEYEVENTF_KEYUP = 2
KEYEVENTF_EXTENDEDKEY = 1
KEYEVENTF_UNICODE = 4


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk',wintypes.WORD),('wScan',wintypes.WORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('dwExtraInfo',ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx',wintypes.LONG),('dy',wintypes.LONG),('mouseData',wintypes.DWORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('dwExtraInfo',ctypes.c_size_t)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki',KEYBDINPUT),('mi',MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ('value',)
    _fields_ = [('type',wintypes.DWORD),('value',INPUTUNION)]


class InputService:
    def __init__(self):
        self._user32 = ctypes.windll.user32
        self._user32.SendInput.argtypes = [wintypes.UINT,ctypes.POINTER(INPUT),ctypes.c_int]
        self._user32.SendInput.restype = wintypes.UINT
        self._user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        self._user32.GetCursorPos.restype = wintypes.BOOL
        self._user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self._user32.GetWindowRect.restype = wintypes.BOOL
        self._user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        self._user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        self.held_buttons = {}
        self._last_cursor = None

    def _focus_target(self, target):
        from core.process_manager import process_manager
        from core.window_manager import restore_window_by_pid, get_process_family_pids, find_visible_window_for_pids, user32
        pid = process_manager.get_pid(target)
        if not pid:
            return False
        hwnd = find_visible_window_for_pids(get_process_family_pids(pid))
        if not hwnd:
            return False
        if user32.GetForegroundWindow() == hwnd:
            return True
        restore_window_by_pid(pid)
        return True

    def _send(self, events):
        if not events:
            return True
        inputs = (INPUT * len(events))(*events)
        res = self._user32.SendInput(len(events), inputs, ctypes.sizeof(INPUT))
        if res != len(events):
            try:
                hdesk = self._user32.OpenInputDesktop(0, False, 0x10000000) or self._user32.OpenDesktopW('Default', 0, False, 0x10000000)
                if hdesk:
                    self._user32.SetThreadDesktop(hdesk)
                    res = self._user32.SendInput(len(events), inputs, ctypes.sizeof(INPUT))
            except Exception:
                pass
        return res == len(events)

    def _key(self, vk, flags=0):
        scan = self._user32.MapVirtualKeyW(vk,0)
        return INPUT(type=1,value=INPUTUNION(ki=KEYBDINPUT(vk,scan,flags,0,0)))

    def send_key(self, key_name, target, browser_back=False, modifiers=()):
        normalized = key_name.upper().strip()
        if browser_back:
            normalized, modifiers = 'LEFT', ('ALT',)
        if normalized == 'SHIFT_TAB':
            normalized, modifiers = 'TAB', ('SHIFT',)
        if normalized == 'SELECT_ALL':
            normalized, modifiers = 'A', ('CTRL',)
        if normalized not in VK_CODES or any(m not in MODIFIERS for m in modifiers):
            return False
        if not self._focus_target(target):
            return False
        flags = KEYEVENTF_EXTENDEDKEY if normalized in ('UP','DOWN','LEFT','RIGHT','HOME','END','DELETE','PAGE_UP','PAGE_DOWN') else 0
        events = [self._key(MODIFIERS[m]) for m in modifiers]
        events += [self._key(VK_CODES[normalized],flags), self._key(VK_CODES[normalized],flags|KEYEVENTF_KEYUP)]
        events += [self._key(MODIFIERS[m],KEYEVENTF_KEYUP) for m in reversed(modifiers)]
        return self._send(events)

    def send_text(self, text, target):
        if not self._focus_target(target):
            return False
        raw = text.encode('utf-16-le')
        events = []
        for i in range(0,len(raw),2):
            code = int.from_bytes(raw[i:i+2],'little')
            for flags in (KEYEVENTF_UNICODE,KEYEVENTF_UNICODE|KEYEVENTF_KEYUP):
                events.append(INPUT(type=1,value=INPUTUNION(ki=KEYBDINPUT(0,code,flags,0,0))))
        return self._send(events)

    def _mouse(self, flags, x=0, y=0, data=0):
        return INPUT(type=0,value=INPUTUNION(mi=MOUSEINPUT(x,y,data & 0xffffffff,flags,0,0)))

    def release_mouse(self, owner=None):
        flags = {'left':4,'right':16}
        buttons = [button for button, held_by in self.held_buttons.items() if owner is None or held_by == owner]
        success = self._send([self._mouse(flags[button]) for button in buttons])
        if success:
            for button in buttons:
                self.held_buttons.pop(button,None)
        return success

    def send_mouse(self, action, target, owner, dx=0, dy=0, wheel=0, button='left'):
        if action == 'release':
            return self.release_mouse(owner)
        if button not in ('left','right') or action not in ('move','wheel','click','down','up'):
            return False
        if self.held_buttons and owner not in self.held_buttons.values():
            return False
        if not self._focus_target(target):
            return False
        from core.process_manager import process_manager
        from core.window_manager import find_visible_window_for_pids, get_process_family_pids
        hwnd = find_visible_window_for_pids(get_process_family_pids(process_manager.get_pid(target)))
        if not hwnd:
            return False
        previous_dpi = self._user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        try:
            rect, point = wintypes.RECT(), wintypes.POINT()
            if not self._user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False
            if not self._user32.GetCursorPos(ctypes.byref(point)):
                point.x, point.y = self._last_cursor or ((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
            x = max(rect.left+2,min(rect.right-3,point.x+int(dx)))
            y = max(rect.top+2,min(rect.bottom-3,point.y+int(dy)))
            self._last_cursor = (x, y)
            events = []
            if action == 'move' or dx != 0 or dy != 0:
                vx,vy,vw,vh = [self._user32.GetSystemMetrics(i) for i in (76,77,78,79)]
                events.append(self._mouse(0xC001,round((x-vx)*65535/max(1,vw-1)),round((y-vy)*65535/max(1,vh-1))))
            down,up = (2,4) if button == 'left' else (8,16)
            if action == 'wheel': events.append(self._mouse(0x0800,data=wheel))
            if action in ('click','down'): events.append(self._mouse(down))
            if action in ('click','up'): events.append(self._mouse(up))
            success = self._send(events)
            if success and action == 'down': self.held_buttons[button] = owner
            if success and action == 'up': self.held_buttons.pop(button,None)
            return success
        finally:
            if previous_dpi: self._user32.SetThreadDpiAwarenessContext(previous_dpi)


input_service = InputService()
