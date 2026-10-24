import os
import ipaddress
import secrets
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
    , "DELETE", "END", "PAGE_UP", "PAGE_DOWN", "SHIFT_TAB", "SELECT_ALL"
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
        
    if not token or not secrets.compare_digest(token, settings.AUTH_TOKEN):
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


def normalize_browser_url(url: str) -> str:
    """Accept a typed web address while keeping non-web protocols forbidden."""
    if not isinstance(url, str) or not url.strip():
        raise HTTPException(status_code=400, detail="Nhập tên miền hoặc địa chỉ IP của website.")
    url = url.strip()
    try:
        if any(ord(char) < 32 or ord(char) == 127 for char in url) or '\\' in url:
            raise ValueError()
        explicit = urllib.parse.urlsplit(url)
        if explicit.scheme and url[len(explicit.scheme):].startswith('://'):
            # Validate the actual scheme below, including unsupported schemes.
            candidate = url
        else:
            if explicit.scheme:
                # urlsplit treats example.com:8080 and localhost:8765 as schemes.
                host_part = url.split(':', 1)[0].lower()
                if host_part != 'localhost' and '.' not in host_part:
                    raise ValueError()
            candidate = 'https:' + url if url.startswith('//') else 'https://' + url
        parsed = urllib.parse.urlsplit(candidate)
        host = parsed.hostname
        if parsed.scheme.lower() not in ('http', 'https') or not host:
            raise ValueError()
        if parsed.username is not None or parsed.password is not None or any(char.isspace() for char in host):
            raise ValueError()
        # Accessing port validates both its numeric form and its allowed range.
        parsed.port
        if not url.lower().startswith(('http://', 'https://')):
            local = host.lower() == 'localhost' or host.lower().endswith('.local')
            try:
                address = ipaddress.ip_address(host)
                local = local or address.is_private or address.is_loopback or address.is_link_local
            except ValueError:
                pass
            candidate = urllib.parse.urlunsplit(parsed._replace(scheme='http' if local else 'https'))
        return validate_url(candidate)
    except ValueError:
        raise HTTPException(status_code=400, detail="Địa chỉ website không hợp lệ. Nhập tên miền hoặc IP; chỉ hỗ trợ HTTP và HTTPS.") from None

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
