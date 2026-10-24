import pytest
from fastapi import HTTPException
from config import settings
from core.security import validate_url, normalize_browser_url, validate_media_path, ALLOWED_KEYS


@pytest.mark.parametrize('typed,expected', [
    ('youtube.com', 'https://youtube.com'),
    ('  example.com/watch?v=1#video  ', 'https://example.com/watch?v=1#video'),
    ('example.com:8080/path', 'https://example.com:8080/path'),
    ('192.168.1.3:8765', 'http://192.168.1.3:8765'),
    ('10.0.0.1/admin', 'http://10.0.0.1/admin'),
    ('127.0.0.1:8080/test', 'http://127.0.0.1:8080/test'),
    ('localhost:8765', 'http://localhost:8765'),
    ('tv.local', 'http://tv.local'),
    ('[::1]:8765', 'http://[::1]:8765'),
    ('//example.com/path', 'https://example.com/path'),
    ('https://192.168.1.3:8765', 'https://192.168.1.3:8765'),
    ('http://example.com', 'http://example.com'),
    ('HTTPS://example.com', 'HTTPS://example.com'),
    ('vídụ.vn', 'https://vídụ.vn'),
])
def test_browser_address_without_protocol(typed, expected):
    assert normalize_browser_url(typed) == expected


@pytest.mark.parametrize('typed', [
    '', '  ', 'javascript:alert(1)', 'data:text/html,hi',
    'file:///C:/Windows', 'ftp://example.com', 'mailto:a@example.com',
    'https://', 'http:example.com', 'example.com:99999',
    'example.com:abc', 'http://[::1', 'https://exa mple.com',
    'https://example.com/\nhello', 'http://example.com\\path',
    'user:password@example.com',
])
def test_browser_address_rejects_invalid_or_unsafe_input(typed):
    with pytest.raises(HTTPException) as error:
        normalize_browser_url(typed)
    assert error.value.status_code == 400

def test_validate_url_valid():
    assert validate_url("http://example.com") == "http://example.com"
    assert validate_url("https://www.youtube.com/watch?v=123") == "https://www.youtube.com/watch?v=123"

def test_validate_url_rejected_schemes():
    with pytest.raises(HTTPException) as exc:
        validate_url("javascript:alert(1)")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        validate_url("file:///C:/Windows/System32/cmd.exe")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        validate_url("data:text/html,<b>hi</b>")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException):
        validate_url("")

def test_allowed_keys_whitelist():
    assert "UP" in ALLOWED_KEYS
    assert "DOWN" in ALLOWED_KEYS
    assert "ENTER" in ALLOWED_KEYS
    assert "ESCAPE" in ALLOWED_KEYS
    assert "MUTE" in ALLOWED_KEYS
    assert "CMD" not in ALLOWED_KEYS
    assert "POWERSHELL" not in ALLOWED_KEYS
    assert "DEL" not in ALLOWED_KEYS

def test_validate_media_path_traversal():
    # Attempting to access sensitive file outside media directory
    with pytest.raises(HTTPException) as exc:
        validate_media_path("C:/Windows/System32/drivers/etc/hosts")
    assert exc.value.status_code == 403

def test_validate_media_path_valid(tmp_path):
    # Add temporary directory to allowed dirs
    settings.ALLOWED_MEDIA_DIRS.append(str(tmp_path))
    test_video = tmp_path / "sample_movie.mp4"
    test_video.write_bytes(b"dummy_video_content")

    valid_path = validate_media_path(str(test_video))
    assert valid_path.name == "sample_movie.mp4"
