from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from core.security import verify_token, ALLOWED_KEYS
from core.app_controller import app_controller

router = APIRouter(prefix="/api/control", tags=["Control"])

class KeyPressRequest(BaseModel):
    key: str = Field(..., description="Tên phím cần bấm (UP, DOWN, LEFT, RIGHT, ENTER, ESCAPE, v.v.)")

class TextInputRequest(BaseModel):
    text: str = Field(..., max_length=256, description="Đoạn văn bản cần gửi tới ứng dụng")

@router.post("/home", dependencies=[Depends(verify_token)])
async def control_home():
    return await app_controller.handle_home()

@router.post("/back", dependencies=[Depends(verify_token)])
async def control_back():
    return await app_controller.handle_back()

@router.post("/press", dependencies=[Depends(verify_token)])
async def control_press(req: KeyPressRequest):
    normalized = req.key.upper().strip()
    if normalized not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Phím '{req.key}' không nằm trong danh sách được phép.")
    return await app_controller.press(normalized)

@router.post("/text", dependencies=[Depends(verify_token)])
async def control_text(req: TextInputRequest):
    return await app_controller.text(req.text)
