import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from pydantic import BaseModel
import json
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import qrcode
import qrcode.image.svg
from config import settings, get_lan_ip, get_lan_adapters
from core.security import verify_token
from core.launcher_service import launcher_service
from core.process_manager import process_manager
from core.state_manager import state_manager
from scripts.server_identity import save_server_identity
from api.routes_status import router as status_router
from api.routes_launcher import router as launcher_router
from api.routes_control import router as control_router
from api.routes_browser import router as browser_router
from api.routes_media import router as media_router
from api.routes_iptv import router as iptv_router
from api.websocket import router as ws_router


class SecretFilter(logging.Filter):
    def filter(self, record):
        record.msg = record.getMessage().replace(settings.AUTH_TOKEN, '[REDACTED]')
        record.args = ()
        return True


log_file = settings.DATA_DIR / 'logs' / 'server.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                    handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding='utf-8')])
for handler in logging.getLogger().handlers:
    handler.addFilter(SecretFilter())
logging.getLogger('uvicorn.error').addFilter(SecretFilter())
logger = logging.getLogger('qsmarttv.server')


async def monitor_processes():
    while True:
        await asyncio.sleep(1)
        await launcher_service.refresh_state()
        if state_manager.active_app in ('browser', 'youtube') and not process_manager.is_running('external_browser'):
            await state_manager.update(active_app='launcher' if launcher_service.is_open() else None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    save_server_identity()
    process_manager.adopt_browser_profile('launcher', settings.BRAVE_PATH, settings.DATA_DIR / 'brave-tv-profile')
    process_manager.adopt_browser_profile('external_browser', settings.BRAVE_PATH, settings.DATA_DIR / 'brave-external-profile')
    if launcher_service.is_open():
        await state_manager.update(launcher='open', active_app='launcher')
    monitor = asyncio.create_task(monitor_processes())
    logger.info('Q Smart TV đang chạy trên cổng %d. Q Remote: http://%s:%d/remote', settings.PORT, get_lan_ip(), settings.PORT)
    try:
        yield
    finally:
        from core.remote_input import remote_input
        from core.brave_service import brave_service
        remote_input.end()
        await brave_service.connection.close()
        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass


app = FastAPI(title='Q Smart TV Server', version='1.0.1', lifespan=lifespan)
for router in (status_router, launcher_router, control_router, browser_router, media_router, iptv_router, ws_router):
    app.include_router(router)
static_dir = Path(__file__).resolve().parent / 'static'
app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')


@app.middleware('http')
async def response_policy(request: Request, call_next):
    response = await call_next(request)
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/health')
def health_check():
    return {'status': 'ok', 'app': 'Q Smart TV'}


@app.get('/')
def index_redirect(request: Request):
    ua = request.headers.get('user-agent', '').lower()
    page = '/remote' if any(m in ua for m in ('mobile', 'android', 'iphone', 'ipad')) else '/tv'
    # Pairing bootstrap is available only on the PC itself, never to a LAN visitor.
    if request.client.host in ('127.0.0.1', '::1'):
        page += f'?token={settings.AUTH_TOKEN}'
    return RedirectResponse(page)


@app.get('/tv', response_class=HTMLResponse)
def serve_tv_ui():
    return (static_dir / 'tv' / 'index.html').read_text(encoding='utf-8')


@app.get('/remote', response_class=HTMLResponse)
def serve_remote_ui():
    return (static_dir / 'remote' / 'index.html').read_text(encoding='utf-8')


@app.get('/api/qrcode', dependencies=[Depends(verify_token)])
def get_remote_qrcode():
    remote_url = f'http://{get_lan_ip()}:{settings.PORT}/remote?token={settings.AUTH_TOKEN}'
    qr_img = qrcode.make(remote_url, image_factory=qrcode.image.svg.SvgPathImage)
    return Response(content=qr_img.to_string(), media_type='image/svg+xml')


@app.get('/api/info', dependencies=[Depends(verify_token)])
def get_system_info():
    lan_ip = get_lan_ip()
    return {'lan_ip': lan_ip, 'port': settings.PORT,
            'network_interfaces': get_lan_adapters(),
            'remote_url': f'http://{lan_ip}:{settings.PORT}/remote?token={settings.AUTH_TOKEN}',
            'brave_available': bool(settings.BRAVE_PATH and Path(settings.BRAVE_PATH).is_file()),
            'mpv_available': bool(settings.MPV_PATH and Path(settings.MPV_PATH).is_file())}


class NetworkSelection(BaseModel):
    ip: str | None = None


@app.post('/api/network', dependencies=[Depends(verify_token)])
def select_network(selection: NetworkSelection):
    if selection.ip and not any(item['ip'] == selection.ip for item in get_lan_adapters()):
        raise HTTPException(400, 'Chọn địa chỉ của Ethernet/Wi-Fi đang hoạt động, không chọn VPN.')
    if settings.LAN_IP:
        raise HTTPException(409, 'QSMART_LAN_IP đang được đặt trong .env. Bỏ cấu hình đó để chọn mạng tại đây.')
    (settings.DATA_DIR / 'config' / 'network.json').write_text(json.dumps({'ip': selection.ip}), encoding='utf-8')
    return {'status': 'success', 'lan_ip': get_lan_ip()}


if __name__ == '__main__':
    uvicorn.run('server:app', host=settings.HOST, port=settings.PORT, log_level='info', access_log=False)
