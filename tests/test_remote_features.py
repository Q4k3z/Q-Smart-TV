import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi.testclient import TestClient
from config import settings, get_lan_adapters, get_lan_ip
from server import app
from core.remote_input import RemoteInput, InputCommand
from core.input_service import input_service
from core.brave_service import brave_service
from core.state_manager import state_manager
from core.process_manager import process_manager
from core.app_controller import app_controller

HEADERS = {'Authorization':f'Bearer {settings.AUTH_TOKEN}'}


def test_lan_ignores_warp_and_virtual_interfaces(monkeypatch):
    import config
    monkeypatch.setattr(config.psutil,'net_if_stats',lambda: {n:SimpleNamespace(isup=True) for n in ('Ethernet','CloudflareWARP','vEthernet')})
    monkeypatch.setattr(config.psutil,'net_if_addrs',lambda: {
        'CloudflareWARP':[SimpleNamespace(family=socket.AF_INET,address='172.16.0.2')],
        'Ethernet':[SimpleNamespace(family=socket.AF_INET,address='192.168.1.3')],
        'vEthernet':[SimpleNamespace(family=socket.AF_INET,address='172.20.0.1')]})
    assert get_lan_adapters() == [{'name':'Ethernet','ip':'192.168.1.3'}]
    assert get_lan_ip() == '192.168.1.3'


def test_network_override_must_be_active_lan(monkeypatch):
    import server, config
    adapters = lambda: [{'name':'Ethernet','ip':'192.168.1.3'},{'name':'Wi-Fi','ip':'192.168.2.4'}]
    monkeypatch.setattr(server,'get_lan_adapters',adapters)
    monkeypatch.setattr(config,'get_lan_adapters',adapters)
    monkeypatch.setattr(settings,'LAN_IP',None)
    client = TestClient(app)
    assert client.post('/api/network',json={'ip':'172.16.0.2'},headers=HEADERS).status_code == 400
    assert client.post('/api/network',json={'ip':'8.8.8.8'},headers=HEADERS).status_code == 400
    assert client.post('/api/network',json={'ip':'192.168.2.4'},headers=HEADERS).json()['lan_ip'] == '192.168.2.4'
    assert get_lan_ip() == '192.168.2.4'
    client.post('/api/network',json={'ip':None},headers=HEADERS)
    assert get_lan_ip() == '192.168.1.3'
    assert client.post('/api/network',json={'ip':None}).status_code == 401


@pytest.mark.asyncio
async def test_backspace_is_not_navigation(monkeypatch):
    state_manager.active_app = 'browser'
    monkeypatch.setattr(process_manager,'is_running',lambda name: name == 'external_browser')
    send = Mock(return_value=True)
    monkeypatch.setattr(input_service,'send_key',send)
    back = AsyncMock()
    monkeypatch.setattr(app_controller,'handle_back',back)
    await app_controller.press('BACKSPACE')
    send.assert_called_once_with('BACKSPACE',target='external_browser')
    back.assert_not_called()


@pytest.mark.asyncio
async def test_home_closes_only_managed_web(monkeypatch):
    close = AsyncMock(return_value=True)
    monkeypatch.setattr(brave_service,'close_external_browser',close)
    from core.launcher_service import launcher_service
    monkeypatch.setattr(launcher_service,'open_launcher',AsyncMock(return_value={'status':'already_running'}))
    assert (await app_controller.handle_home())['status'] == 'success'
    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_back_at_root_returns_home(monkeypatch):
    state_manager.active_app = 'browser'
    monkeypatch.setattr(process_manager,'is_running',lambda name: True)
    monkeypatch.setattr(brave_service,'back',AsyncMock(return_value=False))
    home = AsyncMock(return_value={'status':'success','action':'home'})
    monkeypatch.setattr(app_controller,'handle_home',home)
    assert (await app_controller.handle_back())['action'] == 'home'
    home.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_typing_revision_is_idempotent(monkeypatch):
    service = RemoteInput()
    state_manager.active_app = 'browser'
    monkeypatch.setattr(process_manager,'is_running',lambda name: True)
    monkeypatch.setattr(process_manager,'get_pid',lambda name: 123)
    monkeypatch.setattr(input_service,'_focus_target',lambda target: True)
    monkeypatch.setattr(brave_service,'input_call',AsyncMock(return_value={'ok':True}))
    send = Mock(return_value=True)
    monkeypatch.setattr(input_service,'send_text',send)
    await service.handle('phone',InputCommand(action='input_start'))
    command = InputCommand(action='input_update',text='Tiếng Việt 📺',start=13,end=13)
    await service.handle('phone',command)
    await service.handle('phone',command)
    send.assert_called_once()
    with pytest.raises(RuntimeError):
        await service.handle('phone',InputCommand(action='input_update',revision=3))
    state_manager.active_app = 'launcher'
    with pytest.raises(RuntimeError):
        await service.handle('phone',InputCommand(action='input_update',revision=2))
    assert 'phone' not in service.sessions


def test_mouse_release_only_releases_own_drag(monkeypatch):
    from core.input_service import InputService
    service = InputService()
    service.held_buttons = {'left':'one','right':'two'}
    send = Mock(return_value=True)
    monkeypatch.setattr(service,'_send',send)
    assert service.release_mouse('one')
    assert service.held_buttons == {'right':'two'}
    assert len(send.call_args.args[0]) == 1


@pytest.mark.parametrize('data',[
    {'action':'mouse','dx':501}, {'action':'mouse','mouse':'execute'},
    {'action':'input_update','text':'x'*8001}, {'action':'key','key':'X'*33}])
def test_input_command_limits(data):
    from pydantic import ValidationError
    with pytest.raises(ValidationError): InputCommand(**data)


def test_ws_command_validation_and_disconnect_release(monkeypatch):
    release = Mock(return_value=True)
    monkeypatch.setattr(input_service,'release_mouse',release)
    with TestClient(app) as client, client.websocket_connect(f'/ws?token={settings.AUTH_TOKEN}') as ws:
        assert ws.receive_json()['event'] == 'connected'
        ws.send_json({'id':1,'action':'mouse','dx':999999})
        assert ws.receive_json()['data']['status'] == 'error'
        ws.send_json({'id':2,'action':'release'})
        assert ws.receive_json()['data']['status'] == 'success'
        ws.send_text('ping')
        assert ws.receive_text() == 'pong'
    assert release.call_count >= 2
