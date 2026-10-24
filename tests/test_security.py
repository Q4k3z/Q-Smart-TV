import pytest
from fastapi import HTTPException
from config import settings
from core.security import validate_url, validate_media_path, ALLOWED_KEYS

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
