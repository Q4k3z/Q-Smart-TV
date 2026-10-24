import json
import logging
import re
import uuid
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from config import settings

logger = logging.getLogger("qsmarttv.iptv_service")

class IPTVService:
    def __init__(self):
        self.playlists_file = settings.DATA_DIR / "config" / "iptv_playlists.json"
        self.favorites_file = settings.DATA_DIR / "favorites" / "iptv_favorites.json"
        self._ensure_storage()

    def _ensure_storage(self):
        if not self.playlists_file.is_file():
            default_playlists = []
            self.playlists_file.write_text(json.dumps(default_playlists, ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.favorites_file.is_file():
            self.favorites_file.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_playlists(self) -> List[Dict[str, str]]:
        try:
            return json.loads(self.playlists_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def add_playlist(self, name: str, url: str) -> Dict[str, Any]:
        playlists = self.get_playlists()
        p_id = f"pl_{uuid.uuid4().hex}"
        new_item = {"id": p_id, "name": name, "url": url}
        playlists.append(new_item)
        self.playlists_file.write_text(json.dumps(playlists, ensure_ascii=False, indent=2), encoding="utf-8")
        return new_item

    def delete_playlist(self, p_id: str) -> bool:
        playlists = self.get_playlists()
        filtered = [p for p in playlists if p.get("id") != p_id]
        if len(filtered) != len(playlists):
            self.playlists_file.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        return False

    def load_channels(self, playlist_id: Optional[str] = None, url: Optional[str] = None) -> List[Dict[str, Any]]:
        if not playlist_id and not url:
            channels = []
            for playlist in self.get_playlists():
                channels.extend(self.load_channels(playlist_id=playlist['id']))
            return channels
        target_url = url
        if not target_url and playlist_id:
            for p in self.get_playlists():
                if p.get("id") == playlist_id:
                    target_url = p.get("url")
                    break

        if not target_url:
            return []

        channels = []
        try:
            if target_url.startswith("http://") or target_url.startswith("https://"):
                resp = requests.get(target_url, timeout=5)
                if resp.status_code != 200:
                    logger.error("Không tải được playlist URL: %s - status %d", target_url, resp.status_code)
                    return []
                content = resp.text
            else:
                p_file = Path(target_url)
                if not p_file.is_file():
                    return []
                content = p_file.read_text(encoding="utf-8", errors="ignore")

            current_ch: Optional[Dict[str, Any]] = None
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#EXTINF:"):
                    # Format: #EXTINF:-1 tvg-id="..." group-title="...", Channel Name
                    parts = line[8:].split(",", 1)
                    meta = parts[0]
                    title = parts[1].strip() if len(parts) > 1 else "Kênh không tên"

                    group_match = re.search(r'group-title="([^"]*)"', meta, re.IGNORECASE)
                    group = group_match.group(1).strip() if group_match else "Mặc định"

                    logo_match = re.search(r'tvg-logo="([^"]*)"', meta, re.IGNORECASE)
                    logo = logo_match.group(1).strip() if logo_match else ""

                    current_ch = {
                        "title": title,
                        "group": group,
                        "logo": logo
                    }
                elif not line.startswith("#") and current_ch is not None:
                    current_ch["url"] = line
                    channels.append(current_ch)
                    current_ch = None
        except Exception as e:
            logger.error("Lỗi khi đọc playlist IPTV: %s", str(e))
        return channels

    def get_favorites(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.favorites_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def toggle_favorite(self, channel: Dict[str, Any]) -> bool:
        favs = self.get_favorites()
        url = channel.get("url")
        exists = any(f.get("url") == url for f in favs)
        if exists:
            favs = [f for f in favs if f.get("url") != url]
            added = False
        else:
            favs.append(channel)
            added = True
        self.favorites_file.write_text(json.dumps(favs, ensure_ascii=False, indent=2), encoding="utf-8")
        return added

iptv_service = IPTVService()
