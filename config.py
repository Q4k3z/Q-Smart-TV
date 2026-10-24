import os
import shutil
import socket
import secrets
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8765
    DATA_DIR: Path = BASE_DIR / "data"
    AUTH_TOKEN: Optional[str] = None
    
    # Path configuration
    BRAVE_PATH: Optional[str] = None
    MPV_PATH: Optional[str] = None
    
    # Media directories permitted for playback
    ALLOWED_MEDIA_DIRS: List[str] = []
    
    # IPC Named Pipe for mpv on Windows
    MPV_PIPE_NAME: str = r"\\.\pipe\qsmarttv_mpv"

    model_config = SettingsConfigDict(
        env_prefix="QSMART_",
        env_file=".env",
        extra="ignore"
    )

def get_lan_ip() -> str:
    """Finds the most likely local Wi-Fi / Ethernet LAN IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def find_brave_executable() -> Optional[str]:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    which_brave = shutil.which("brave")
    if which_brave:
        candidates.insert(0, which_brave)
        
    for p in candidates:
        if p and os.path.isfile(p):
            return p

    # Fallback candidates if Brave is missing (e.g. Chrome, Edge)
    fallbacks = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for fb in fallbacks:
        if fb and os.path.isfile(fb):
            return fb
    return None

def find_mpv_executable() -> Optional[str]:
    candidates = [
        r"C:\Program Files\MPV Player\mpv.exe",
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\mpv\mpv.exe",
        r"C:\tools\mpv\mpv.exe",
    ]
    which_mpv = shutil.which("mpv")
    if which_mpv:
        candidates.insert(0, which_mpv)
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None

def load_or_generate_token(data_dir: Path) -> str:
    token_file = data_dir / "config" / "auth_token.txt"
    if token_file.is_file():
        t = token_file.read_text(encoding="utf-8").strip()
        if len(t) >= 16:
            return t
    token_file.parent.mkdir(parents=True, exist_ok=True)
    new_token = secrets.token_urlsafe(24)
    token_file.write_text(new_token, encoding="utf-8")
    return new_token

settings = Settings()

# Ensure data folders
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "config").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "playlists").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "favorites").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "brave-tv-profile").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "brave-external-profile").mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "media").mkdir(parents=True, exist_ok=True)

if not settings.AUTH_TOKEN:
    settings.AUTH_TOKEN = load_or_generate_token(settings.DATA_DIR)

if not settings.BRAVE_PATH:
    settings.BRAVE_PATH = find_brave_executable()

if not settings.MPV_PATH:
    settings.MPV_PATH = find_mpv_executable()

# Default allowed media directories
user_videos = os.path.expandvars(r"%USERPROFILE%\Videos")
default_media = [str(settings.DATA_DIR / "media")]
if os.path.isdir(user_videos):
    default_media.append(user_videos)
for p in settings.ALLOWED_MEDIA_DIRS:
    if p not in default_media:
        default_media.append(p)
settings.ALLOWED_MEDIA_DIRS = default_media
