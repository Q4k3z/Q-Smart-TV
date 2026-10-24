import pytest
from core.launcher_service import launcher_service
from core.state_manager import state_manager

@pytest.mark.asyncio
async def test_launcher_exit_when_closed():
    # If launcher is not open, exit returns already_closed without error
    res = await launcher_service.exit_launcher()
    assert res["status"] in ("already_closed", "success")
    assert state_manager.launcher == "closed"
