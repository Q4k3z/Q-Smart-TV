from fastapi import APIRouter, Depends
from core.security import verify_token
from core.app_controller import app_controller

router = APIRouter(prefix="/api/launcher", tags=["Launcher"])

@router.post("/open", dependencies=[Depends(verify_token)])
async def open_launcher():
    """Opens launcher interface on TV if closed."""
    return await app_controller.reopen_tv()

@router.post("/exit", dependencies=[Depends(verify_token)])
async def exit_launcher():
    """Closes TV launcher interface. FastAPI server remains running."""
    return await app_controller.exit_tv()
