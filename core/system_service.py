import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger("qsmarttv.system_service")

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm", ".ts"}

class SystemService:
    def scan_movies(self) -> List[Dict[str, Any]]:
        movies = []
        for media_dir_str in settings.ALLOWED_MEDIA_DIRS:
            media_dir = Path(media_dir_str).resolve()
            if not media_dir.is_dir():
                continue
            
            try:
                for entry in os.scandir(media_dir):
                    if entry.is_file() and Path(entry.name).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                        size_mb = round(entry.stat().st_size / (1024 * 1024), 2)
                        movies.append({
                            "title": Path(entry.name).stem,
                            "filename": entry.name,
                            "path": str(Path(entry.path).resolve()),
                            "size_mb": size_mb,
                            "directory": str(media_dir)
                        })
                    elif entry.is_dir():
                        # Subfolder scan (1 level)
                        try:
                            for sub_entry in os.scandir(entry.path):
                                if sub_entry.is_file() and Path(sub_entry.name).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                                    size_mb = round(sub_entry.stat().st_size / (1024 * 1024), 2)
                                    movies.append({
                                        "title": Path(sub_entry.name).stem,
                                        "filename": sub_entry.name,
                                        "path": str(Path(sub_entry.path).resolve()),
                                        "size_mb": size_mb,
                                        "directory": str(media_dir)
                                    })
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError) as e:
                logger.error("Không thể quét thư mục media [%s]: %s", media_dir, str(e))
                continue
        return movies

system_service = SystemService()
