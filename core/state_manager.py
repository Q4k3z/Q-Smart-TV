import asyncio
import datetime
from typing import Optional, Dict, Any
from core.event_bus import event_bus

class StateManager:
    def __init__(self):
        self.server: str = "online"
        self.launcher: str = "closed"  # "open" or "closed"
        self.active_app: Optional[str] = None  # "launcher", "youtube", "browser", "movies", "iptv"
        self.mpv: str = "stopped"  # "stopped", "starting", "playing", "paused", "error"
        self.current_media: Optional[Dict[str, Any]] = None
        self.updated_at: str = datetime.datetime.now().isoformat()
        self._lock = asyncio.Lock()

    def get_state(self) -> dict:
        from core.process_manager import process_manager
        return {
            "server": self.server,
            "launcher": self.launcher,
            "active_app": self.active_app,
            "mpv": self.mpv,
            "brave": "open" if process_manager.is_running("external_browser") else "closed",
            "current_media": self.current_media,
            "updated_at": self.updated_at
        }

    async def update(self, **kwargs):
        async with self._lock:
            changed = False
            for k, v in kwargs.items():
                if hasattr(self, k) and getattr(self, k) != v:
                    setattr(self, k, v)
                    changed = True
            
            if changed:
                self.updated_at = datetime.datetime.now().isoformat()
                payload = {
                    "event": "state_changed",
                    "data": self.get_state()
                }
                # Broadcast via event_bus
                asyncio.create_task(event_bus.broadcast(payload))

state_manager = StateManager()
