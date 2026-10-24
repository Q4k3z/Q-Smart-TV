import asyncio
import logging
from unittest.mock import Mock, AsyncMock
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from server import app, SecretFilter
from config import settings
from core.app_controller import app_controller
from core.launcher_service import launcher_service
from core.process_manager import process_manager
from core.state_manager import state_manager
from core.mpv_service import mpv_service
from core.brave_service import brave_service
import core.launcher_service as launcher_module

HEADERS = {'Authorization': f'Bearer {settings.AUTH_TOKEN}'}


def test_pairing_does_not_leak_to_lan():
    client = TestClient(app, client=('192.168.1.10', 50000))
    for path in ('/api/info', '/api/qrcode'):
        assert client.get(path).status_code == 401
        assert settings.AUTH_TOKEN not in client.get(path).text
    assert 'token=' not in client.get('/', follow_redirects=False).headers['location']
    assert client.get('/remote').headers['referrer-policy'] == 'no-referrer'


def test_local_bootstrap_and_remote_auth():
    client = TestClient(app, client=('127.0.0.1', 50000))
    assert settings.AUTH_TOKEN in client.get('/', follow_redirects=False).headers['location']
    assert client.get('/api/info', headers=HEADERS).status_code == 200
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws?token=wrong'):
            pass


def test_tv_role_only_allowed_on_pc():
    client = TestClient(app, client=('192.168.1.10', 50000))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f'/ws?role=tv&token={settings.AUTH_TOKEN}'):
            pass


def test_remote_commands_reach_tv_without_native_input():
    state_manager.active_app = 'launcher'
    with TestClient(app, client=('127.0.0.1', 50000)) as client, client.websocket_connect(f'/ws?role=tv&token={settings.AUTH_TOKEN}') as tv:
        assert tv.receive_json()['event'] == 'connected'
        response = client.post('/api/control/press', headers=HEADERS, json={'key':'DOWN'})
        assert response.status_code == 200
        assert tv.receive_json() == {'event':'control', 'data':{'action':'key', 'key':'DOWN'}}
        assert client.post('/api/control/back', headers=HEADERS).status_code == 200
        assert tv.receive_json()['data']['action'] == 'back'


@pytest.mark.asyncio
async def test_exit_only_closes_launcher(monkeypatch):
    close_launcher = AsyncMock(return_value={'status':'success'})
    stop_media = AsyncMock()
    close_browser = AsyncMock()
    monkeypatch.setattr(launcher_service, 'exit_launcher', close_launcher)
    monkeypatch.setattr(mpv_service, 'stop', stop_media)
    monkeypatch.setattr(brave_service, 'close_external_browser', close_browser)
    assert (await app_controller.exit_tv())['status'] == 'success'
    close_launcher.assert_awaited_once()
    stop_media.assert_not_called()
    close_browser.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_open_has_one_process(monkeypatch):
    running = False
    def register(name, pid):
        nonlocal running
        running = True
    monkeypatch.setattr(settings, 'BRAVE_PATH', 'brave.exe')
    monkeypatch.setattr(process_manager, 'is_running', lambda name: running)
    monkeypatch.setattr(process_manager, 'register_process', register)
    monkeypatch.setattr(process_manager, 'get_pid', lambda name: 123)
    spawn = Mock(return_value=Mock(pid=123))
    monkeypatch.setattr(launcher_module.subprocess, 'Popen', spawn)
    monkeypatch.setattr(launcher_module, 'wait_for_window_by_pid', lambda *a, **kw: 12345)
    monkeypatch.setattr(launcher_module, 'force_foreground_window', lambda hwnd: True)
    monkeypatch.setattr(launcher_module, 'restore_window_by_pid', lambda pid: True)
    results = await asyncio.gather(*(launcher_service.open_launcher() for _ in range(5)))
    assert spawn.call_count == 1
    assert [r['status'] for r in results].count('success') == 1
    assert state_manager.launcher == 'open'


@pytest.mark.asyncio
async def test_no_window_is_not_success(monkeypatch):
    monkeypatch.setattr(settings, 'BRAVE_PATH', 'missing.exe')
    monkeypatch.setattr(launcher_module.subprocess, 'Popen', Mock(return_value=Mock(pid=123)))
    monkeypatch.setattr(process_manager, 'register_process', Mock())
    monkeypatch.setattr(launcher_module, 'wait_for_window_by_pid', lambda *a, **kw: None)
    monkeypatch.setattr(process_manager, 'terminate_process', AsyncMock(return_value=True))
    assert (await launcher_service.open_launcher())['status'] == 'error'
    assert state_manager.launcher == 'closed'


@pytest.mark.asyncio
async def test_manual_launcher_close_refreshes_status(monkeypatch):
    state_manager.launcher = 'open'
    state_manager.active_app = 'launcher'
    await launcher_service.refresh_state()
    assert state_manager.launcher == 'closed'
    assert state_manager.active_app is None


@pytest.mark.asyncio
async def test_failed_exit_preserves_open_state(monkeypatch):
    state_manager.launcher = 'open'
    monkeypatch.setattr(process_manager, 'is_running', lambda name: True)
    monkeypatch.setattr(process_manager, 'terminate_process', AsyncMock(return_value=False))
    assert (await launcher_service.exit_launcher())['status'] == 'error'
    assert state_manager.launcher == 'open'


@pytest.mark.asyncio
async def test_foreground_denied_never_kills_existing_window(monkeypatch):
    monkeypatch.setattr(process_manager, 'is_running', lambda name: True)
    monkeypatch.setattr(process_manager, 'get_pid', lambda name: 123)
    monkeypatch.setattr(launcher_module, 'restore_window_by_pid', lambda pid: False)
    monkeypatch.setattr(launcher_module, 'get_process_family_pids', lambda pid: [123])
    monkeypatch.setattr(launcher_module, 'find_visible_window_for_pids', lambda pids: 12345)
    terminate = AsyncMock()
    monkeypatch.setattr(process_manager, 'terminate_process', terminate)
    result = await launcher_service.open_launcher()
    assert result['status'] == 'already_running'
    assert result['foreground'] is False
    terminate.assert_not_called()


def test_log_redacts_pairing_secret():
    record = logging.LogRecord('test', logging.INFO, '', 1, 'url?token=%s', (settings.AUTH_TOKEN,), None)
    SecretFilter().filter(record)
    assert settings.AUTH_TOKEN not in record.getMessage()


def test_stop_does_not_touch_arbitrary_listener(monkeypatch):
    from scripts import stop_server
    monkeypatch.setattr(stop_server, 'managed_server_process', lambda: None)
    terminate = Mock()
    monkeypatch.setattr(stop_server.psutil.Process, 'terminate', terminate)
    assert stop_server.stop_server() == 0
    terminate.assert_not_called()


def test_input_unicode_uses_correct_windows_structure(monkeypatch):
    import ctypes
    from core.input_service import input_service, INPUT
    sent = []
    fake = Mock()
    def capture(count, items, size):
        sent.extend((items[i].ki.wScan, items[i].ki.dwFlags) for i in range(count))
        assert size == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
        return count
    fake.SendInput = capture
    monkeypatch.setattr(input_service, '_user32', fake)
    monkeypatch.setattr(input_service, '_focus_target', lambda target: True)
    assert input_service.send_text('Việt 📺', target='external_browser')
    expected_units = len('Việt 📺'.encode('utf-16-le')) // 2
    assert len(sent) == expected_units * 2
    assert sent[0][1] == 4 and sent[1][1] == 6


def test_config_rejects_weak_tokens_and_invalid_ports():
    from config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(AUTH_TOKEN='weak')
    with pytest.raises(ValidationError):
        Settings(PORT=70000)


def test_no_api_file_reads_for_playlist_query():
    client = TestClient(app)
    res = client.get('/api/iptv/channels', params={'url':'C:/Windows/win.ini'}, headers=HEADERS)
    assert res.status_code == 400


def test_adopt_only_exact_private_browser_profile(monkeypatch):
    from core.process_manager import ProcessManager
    manager = ProcessManager()
    profile = settings.DATA_DIR / 'brave-tv-profile'
    good = Mock(pid=12, info={'exe':'C:/Brave/brave.exe', 'cmdline':['brave.exe',f'--user-data-dir={profile}']})
    other = Mock(pid=13, info={'exe':'C:/Brave/brave.exe', 'cmdline':['brave.exe','--user-data-dir=C:/Personal']})
    import psutil
    monkeypatch.setattr(psutil, 'process_iter', lambda attrs: [other,good])
    registered = Mock()
    monkeypatch.setattr(manager, 'register_process', registered)
    manager.adopt_browser_profile('launcher','C:/Brave/brave.exe',profile)
    registered.assert_called_once_with('launcher',12)
