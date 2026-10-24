from fastapi import APIRouter, Depends
from core.security import verify_token
from core.state_manager import state_manager

router = APIRouter(prefix="/api/status", tags=["Status"])

@router.get("", dependencies=[Depends(verify_token)])
async def get_system_status():
    """Returns current system, launcher, and media player status."""
    return state_manager.get_state()
