import os
import shutil
import socket
import secrets
import json
import ipaddress
import psutil
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8765, ge=1, le=65535)
    DATA_DIR: Path = BASE_DIR / "data"
    AUTH_TOKEN: Optional[str] = None
    LAN_IP: Optional[str] = None
    
    # Path configuration
    BRAVE_PATH: Optional[str] = None
    MPV_PATH: Optional[str] = None
    
    # Media directories permitted for playback
    ALLOWED_MEDIA_DIRS: List[str] = []
    
    # IPC Named Pipe for mpv on Windows
    MPV_PIPE_NAME: str = r"\\.\pipe\qsmarttv_mpv"

    @field_validator('AUTH_TOKEN')
    @classmethod
    def secure_token(cls, value):
        if not value:
            return None
        if len(value) < 24:
            raise ValueError('QSMART_AUTH_TOKEN phải có ít nhất 24 ký tự hoặc bỏ trống để tự tạo.')
        return value

    model_config = SettingsConfigDict(
        env_prefix="QSMART_",
        env_file=BASE_DIR / ".env",
        extra="ignore"
    )

def get_lan_ip() -> str:
    adapters = get_lan_adapters()
    selected = settings.LAN_IP
    try:
        selected = selected or json.loads((settings.DATA_DIR / 'config' / 'network.json').read_text(encoding='utf-8')).get('ip')
    except (OSError, ValueError):
        pass
    if selected and any(a['ip'] == selected for a in adapters):
        return selected
    return adapters[0]['ip'] if adapters else '127.0.0.1'


def get_lan_adapters() -> list:
    """Advertise physical LAN interfaces, never a VPN's Internet route."""
    ignored = ('warp', 'vpn', 'tunnel', 'tailscale', 'zerotier', 'wireguard',
               'virtual', 'vethernet', 'vmware', 'virtualbox', 'loopback', 'bluetooth', 'tap-', 'tun-')
    stats = psutil.net_if_stats()
    result = []
    for name, addresses in psutil.net_if_addrs().items():
        if any(part in name.lower() for part in ignored) or not stats.get(name) or not stats[name].isup:
            continue
        for address in addresses:
            if address.family != socket.AF_INET:
                continue
            ip = ipaddress.ip_address(address.address)
            if ip.is_private and not (ip.is_loopback or ip.is_link_local or ip.is_unspecified):
                result.append({'name': name, 'ip': str(ip)})
    return sorted(result, key=lambda a: (not any(x in a['name'].lower() for x in ('ethernet', 'wi-fi', 'wifi', 'wlan')), a['name'], a['ip']))

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
    # The old auth_token.txt was committed publicly; never reuse that credential.
    token_file = data_dir / "config" / "pairing_token.txt"
    if token_file.is_file():
        t = token_file.read_text(encoding="utf-8").strip()
        if len(t) >= 24:
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
default_media = [str(settings.DATA_DIR / "media")]
for p in settings.ALLOWED_MEDIA_DIRS:
    if p not in default_media:
        default_media.append(p)
settings.ALLOWED_MEDIA_DIRS = default_media
