import os
import io
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import qrcode
import qrcode.image.svg

from config import settings, get_lan_ip
from api.routes_status import router as status_router
from api.routes_launcher import router as launcher_router
from api.routes_control import router as control_router
from api.routes_browser import router as browser_router
from api.routes_media import router as media_router
from api.routes_iptv import router as iptv_router
from api.websocket import router as ws_router

# Setup logging
log_file = settings.DATA_DIR / "logs" / "server.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("qsmarttv.server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    lan_ip = get_lan_ip()
    logger.info("==================================================")
    logger.info("  Q SMART TV SERVER ĐÃ KHỞI ĐỘNG THÀNH CÔNG       ")
    logger.info("  Màn hình TV:    http://127.0.0.1:%d/tv", settings.PORT)
    logger.info("  Điện thoại LAN: http://%s:%d/remote", lan_ip, settings.PORT)
    logger.info("==================================================")
    yield
    logger.info("Q Smart TV Server đang dừng...")

app = FastAPI(title="Q Smart TV Server", version="1.0.0", lifespan=lifespan)

# Local LAN CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(status_router)
app.include_router(launcher_router)
app.include_router(control_router)
app.include_router(browser_router)
app.include_router(media_router)
app.include_router(iptv_router)
app.include_router(ws_router)

# Mount Static Folders
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "tv").mkdir(parents=True, exist_ok=True)
(static_dir / "remote").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "Q Smart TV"}

@app.get("/")
def index_redirect(request: Request):
    ua = request.headers.get("user-agent", "").lower()
    is_mobile = any(m in ua for m in ["mobile", "android", "iphone", "ipad"])
    if is_mobile:
        return RedirectResponse(url=f"/remote?token={settings.AUTH_TOKEN}")
    return RedirectResponse(url=f"/tv?token={settings.AUTH_TOKEN}")

@app.get("/tv", response_class=HTMLResponse)
def serve_tv_ui():
    tv_index = static_dir / "tv" / "index.html"
    if tv_index.is_file():
        return tv_index.read_text(encoding="utf-8")
    return "<h1>Q Smart TV Launcher UI đang được chuẩn bị...</h1>"

@app.get("/remote", response_class=HTMLResponse)
def serve_remote_ui():
    remote_index = static_dir / "remote" / "index.html"
    if remote_index.is_file():
        return remote_index.read_text(encoding="utf-8")
    return "<h1>Q Remote UI đang được chuẩn bị...</h1>"

@app.get("/api/qrcode")
def get_remote_qrcode(token: str = Query(None)):
    """Generates an SVG QR Code containing the URL to pair phone with Q Remote."""
    lan_ip = get_lan_ip()
    target_token = token if token else settings.AUTH_TOKEN
    remote_url = f"http://{lan_ip}:{settings.PORT}/remote?token={target_token}"
    
    factory = qrcode.image.svg.SvgPathImage
    qr_img = qrcode.make(remote_url, image_factory=factory)
    svg_data = qr_img.to_string()
    return Response(content=svg_data, media_type="image/svg+xml")

@app.get("/api/info")
def get_system_info():
    """Returns basic LAN network and pairing information."""
    lan_ip = get_lan_ip()
    return {
        "lan_ip": lan_ip,
        "port": settings.PORT,
        "remote_url": f"http://{lan_ip}:{settings.PORT}/remote?token={settings.AUTH_TOKEN}"
    }

if __name__ == "__main__":
    uvicorn.run("server:app", host=settings.HOST, port=settings.PORT, log_level="info")
