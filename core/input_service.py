import ctypes
import time
import logging
from typing import Optional

logger = logging.getLogger("qsmarttv.input_service")

# Win32 Virtual-Key Codes
VK_CODES = {
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "ENTER": 0x0D,
    "ESCAPE": 0x1B,
    "BACKSPACE": 0x08,
    "HOME": 0x24,
    "TAB": 0x09,
    "SPACE": 0x20,
    "VOLUME_MUTE": 0xAD,
    "VOLUME_DOWN": 0xAE,
    "VOLUME_UP": 0xAF,
    "MEDIA_PLAY_PAUSE": 0xB3,
    "MEDIA_STOP": 0xB2,
    "MEDIA_NEXT_TRACK": 0xB0,
    "MEDIA_PREV_TRACK": 0xB1,
    # Aliases
    "MUTE": 0xAD,
    "PLAY_PAUSE": 0xB3,
    "STOP": 0xB2,
}

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_UNICODE = 0x0004

class InputService:
    def __init__(self):
        self._user32 = ctypes.windll.user32

    def send_key(self, key_name: str) -> bool:
        normalized = key_name.upper().strip()
        vk = VK_CODES.get(normalized)
        if not vk:
            logger.warning("Phím không được hỗ trợ hoặc không hợp lệ: %s", key_name)
            return False

        scan = self._user32.MapVirtualKeyW(vk, 0)
        flags_down = 0
        if normalized in ("UP", "DOWN", "LEFT", "RIGHT", "HOME", "VOLUME_UP", "VOLUME_DOWN", "VOLUME_MUTE", "MEDIA_PLAY_PAUSE"):
            flags_down |= KEYEVENTF_EXTENDEDKEY

        try:
            self._user32.keybd_event(vk, scan, flags_down, 0)
            self._user32.keybd_event(vk, scan, flags_down | KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            logger.error("Lỗi khi gửi phím %s: %s", key_name, str(e))
            return False

    def send_text(self, text: str) -> bool:
        """Sends unicode characters as keystrokes to active window."""
        if not text:
            return True
        try:
            for ch in text:
                code = ord(ch)
                self._user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
                self._user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
                time.sleep(0.01)
            return True
        except Exception as e:
            logger.error("Lỗi khi gửi văn bản: %s", str(e))
            return False

input_service = InputService()
