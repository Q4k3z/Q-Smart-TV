import os
import urllib.parse
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, Security, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

security_bearer = HTTPBearer(auto_error=False)

ALLOWED_KEYS = {
    "UP", "DOWN", "LEFT", "RIGHT",
    "ENTER", "ESCAPE", "BACKSPACE",
    "HOME", "TAB", "SPACE",
    "VOLUME_UP", "VOLUME_DOWN", "MUTE", "PLAY_PAUSE"
}

def verify_token(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> bool:
    """Verifies that the request provides a valid token via Bearer header or ?token= query param."""
    token = None
    if auth and auth.credentials:
        token = auth.credentials
    if not token:
        token = request.query_params.get("token")
        
    if not token or token != settings.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc thiếu thông tin xác thực."
        )
    return True

def validate_url(url: str) -> str:
    """Validates that a URL strictly uses http or https scheme and is safe to open."""
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="URL không hợp lệ.")
    
    url = url.strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận địa chỉ website có giao thức http:// hoặc https://."
        )
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Địa chỉ website thiếu tên miền hợp lệ.")
    return url

def validate_media_path(file_path_str: str) -> Path:
    """Ensures file is strictly inside one of the allowed media directories (no directory traversal)."""
    if not file_path_str or not isinstance(file_path_str, str):
        raise HTTPException(status_code=400, detail="Đường dẫn tệp không hợp lệ.")
    
    target_path = Path(file_path_str).resolve()
    
    allowed = False
    for allowed_dir in settings.ALLOWED_MEDIA_DIRS:
        base_allowed = Path(allowed_dir).resolve()
        try:
            target_path.relative_to(base_allowed)
            allowed = True
            break
        except ValueError:
            continue
            
    if not allowed or not target_path.is_file():
        raise HTTPException(
            status_code=403,
            detail="Tệp video không tồn tại hoặc nằm ngoài danh sách thư mục được phép."
        )
    
    # Supported video formats
    valid_exts = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm", ".flv", ".ts"}
    if target_path.suffix.lower() not in valid_exts:
        raise HTTPException(status_code=400, detail="Định dạng tệp không được hỗ trợ phát.")
        
    return target_path
