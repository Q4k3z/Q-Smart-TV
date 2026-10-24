from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from core.security import verify_token
from core.brave_service import brave_service

router = APIRouter(prefix="/api/browser", tags=["Browser"])

class OpenUrlRequest(BaseModel):
    url: str = Field(..., description="Địa chỉ web HTTP hoặc HTTPS")

class YouTubeRequest(BaseModel):
    query: str = Field(default="", max_length=200, description="Từ khóa tìm kiếm YouTube")

@router.post("/open", dependencies=[Depends(verify_token)])
async def open_browser_url(req: OpenUrlRequest):
    return await brave_service.open_url(req.url)

@router.post("/youtube", dependencies=[Depends(verify_token)])
async def open_youtube(req: YouTubeRequest):
    return await brave_service.open_youtube(req.query)
