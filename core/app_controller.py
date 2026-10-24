import logging
from core.launcher_service import launcher_service
from core.brave_service import brave_service
from core.mpv_service import mpv_service
from core.input_service import input_service
from core.state_manager import state_manager

logger = logging.getLogger("qsmarttv.app_controller")

class AppController:
    async def handle_home(self) -> dict:
        """Handles Home button navigation."""
        logger.info("Xử lý nút Home.")
        # If mpv is playing, stop it so we don't leave zombie media players
        if mpv_service.is_running():
            await mpv_service.stop()

        # If external browser (YouTube or website) is open, close it cleanly
        await brave_service.close_external_browser()

        # Ensure launcher is running
        if not launcher_service.is_open():
            await launcher_service.open_launcher()
        else:
            # Send HOME key or focus
            input_service.send_key("HOME")
            await state_manager.update(active_app="launcher")

        return {"status": "success", "action": "home"}

    async def handle_back(self) -> dict:
        """Handles Back button navigation."""
        logger.info("Xử lý nút Back.")
        # If mpv is running, don't stop media abruptly unless commanded, but ESC can exit fullscreen or go back
        input_service.send_key("ESCAPE")
        return {"status": "success", "action": "back"}

    async def exit_tv(self) -> dict:
        """Exits TV launcher only. Server and Remote remain online."""
        # Stop any active media before closing launcher
        if mpv_service.is_running():
            await mpv_service.stop()
        await brave_service.close_external_browser()
        return await launcher_service.exit_launcher()

    async def reopen_tv(self) -> dict:
        """Reopens launcher on TV screen."""
        return await launcher_service.open_launcher()

app_controller = AppController()
