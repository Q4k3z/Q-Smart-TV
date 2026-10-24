from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from core.security import verify_token, validate_url
from core.iptv_service import iptv_service
from core.mpv_service import mpv_service

router = APIRouter(prefix="/api/iptv", tags=["IPTV"])

class AddPlaylistRequest(BaseModel):
    name: str = Field(..., max_length=100, description="Tên gợi nhớ cho playlist")
    url: str = Field(..., description="Đường dẫn URL hoặc tệp M3U/M3U8")

class PlayStreamRequest(BaseModel):
    url: str = Field(..., description="URL luồng phát HLS / HTTP")
    title: str = Field(default="", description="Tên kênh truyền hình")

class ChannelFavoriteRequest(BaseModel):
    channel: dict = Field(..., description="Thông tin kênh IPTV")

@router.get("/playlists", dependencies=[Depends(verify_token)])
async def get_playlists():
    return iptv_service.get_playlists()

@router.post("/playlists", dependencies=[Depends(verify_token)])
async def add_playlist(req: AddPlaylistRequest):
    valid_url = validate_url(req.url)
    return iptv_service.add_playlist(req.name, valid_url)

@router.delete("/playlists/{playlist_id}", dependencies=[Depends(verify_token)])
async def delete_playlist(playlist_id: str):
    success = iptv_service.delete_playlist(playlist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy playlist.")
    return {"status": "success", "deleted": playlist_id}

@router.get("/channels", dependencies=[Depends(verify_token)])
def get_channels(
    playlist_id: Optional[str] = Query(None),
    url: Optional[str] = Query(None)
):
    if url:
        # The query may fetch HTTP playlists, never arbitrary files on the PC.
        url = validate_url(url)
    return iptv_service.load_channels(playlist_id=playlist_id, url=url)

@router.post("/play", dependencies=[Depends(verify_token)])
async def play_channel(req: PlayStreamRequest):
    valid_url = validate_url(req.url)
    title = req.title if req.title else "Kênh IPTV"
    return await mpv_service.play(valid_url, title=title, is_stream=True)

@router.get("/favorites", dependencies=[Depends(verify_token)])
async def get_favorites():
    return iptv_service.get_favorites()

@router.post("/favorites", dependencies=[Depends(verify_token)])
async def toggle_favorite(req: ChannelFavoriteRequest):
    added = iptv_service.toggle_favorite(req.channel)
    return {"status": "success", "favorited": added}
