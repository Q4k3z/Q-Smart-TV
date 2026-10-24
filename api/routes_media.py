from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from core.security import verify_token, validate_media_path
from core.mpv_service import mpv_service
from core.system_service import system_service
from core.state_manager import state_manager

router = APIRouter(prefix="/api/media", tags=["Media"])

class PlayFileRequest(BaseModel):
    path: str = Field(..., description="Đường dẫn tuyệt đối của tệp video trên máy chủ")
    title: str = Field(default="", description="Tiêu đề hiển thị")

class SeekRequest(BaseModel):
    seconds: float = Field(..., description="Số giây cần tua (+ hoặc -)")

class VolumeRequest(BaseModel):
    delta: int = Field(..., description="Độ thay đổi âm lượng (+5, -5, v.v.)")

@router.get("/movies", dependencies=[Depends(verify_token)])
async def list_movies():
    """Lists scanned offline movies from allowed media folders."""
    return system_service.scan_movies()

@router.post("/play", dependencies=[Depends(verify_token)])
async def play_file(req: PlayFileRequest):
    valid_path = validate_media_path(req.path)
    title = req.title if req.title else valid_path.stem
    return await mpv_service.play(str(valid_path), title=title, is_stream=False)

@router.post("/pause", dependencies=[Depends(verify_token)])
async def pause_media():
    return await mpv_service.pause_toggle()

@router.post("/stop", dependencies=[Depends(verify_token)])
async def stop_media():
    return await mpv_service.stop()

@router.post("/seek", dependencies=[Depends(verify_token)])
async def seek_media(req: SeekRequest):
    return await mpv_service.seek(req.seconds)

@router.post("/volume", dependencies=[Depends(verify_token)])
async def adjust_volume(req: VolumeRequest):
    return await mpv_service.volume_change(req.delta)

@router.get("/status", dependencies=[Depends(verify_token)])
async def media_status():
    return {
        "mpv": state_manager.mpv,
        "current_media": state_manager.current_media
    }
