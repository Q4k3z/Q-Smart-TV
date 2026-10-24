from fastapi.testclient import TestClient
from server import app
from config import settings

client = TestClient(app)

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "app": "Q Smart TV"}

def test_status_without_token():
    res = client.get("/api/status")
    assert res.status_code == 401

def test_status_with_valid_token():
    headers = {"Authorization": f"Bearer {settings.AUTH_TOKEN}"}
    res = client.get("/api/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "server" in data
    assert "launcher" in data
    assert data["server"] == "online"

def test_control_press_allowed_key():
    headers = {"Authorization": f"Bearer {settings.AUTH_TOKEN}"}
    res = client.post("/api/control/press", headers=headers, json={"key": "UP"})
    assert res.status_code == 409  # No managed TV window: never inject into another app.

def test_control_press_disallowed_key():
    headers = {"Authorization": f"Bearer {settings.AUTH_TOKEN}"}
    res = client.post("/api/control/press", headers=headers, json={"key": "INVALID_KEY_XXX"})
    assert res.status_code == 400

def test_browser_open_disallowed_scheme():
    headers = {"Authorization": f"Bearer {settings.AUTH_TOKEN}"}
    res = client.post("/api/browser/open", headers=headers, json={"url": "file:///C:/Windows"})
    assert res.status_code == 400

def test_qrcode_generation():
    res = client.get("/api/qrcode", headers={"Authorization": f"Bearer {settings.AUTH_TOKEN}"})
    assert res.status_code == 200
    assert "image/svg+xml" in res.headers["content-type"]
    assert b"<svg" in res.content

def test_system_info():
    res = client.get("/api/info", headers={"Authorization": f"Bearer {settings.AUTH_TOKEN}"})
    assert res.status_code == 200
    data = res.json()
    assert "lan_ip" in data
    assert "port" in data
    assert "remote_url" in data
    assert str(settings.PORT) in data["remote_url"]
