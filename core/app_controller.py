import logging
from core.launcher_service import launcher_service
from core.brave_service import brave_service
from core.mpv_service import mpv_service
from core.input_service import input_service
from core.state_manager import state_manager
from core.process_manager import process_manager
from core.window_manager import restore_window_by_pid

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

        # Ensure launcher is running and restored to foreground
        if not launcher_service.is_open():
            await launcher_service.open_launcher()
        else:
            launcher_pid = process_manager.get_pid("launcher")
            if launcher_pid:
                restore_window_by_pid(launcher_pid)
            input_service.send_key("HOME")
            await state_manager.update(active_app="launcher")

        return {"status": "success", "action": "home"}

    async def handle_back(self) -> dict:
        """Handles Back button navigation."""
        logger.info("Xử lý nút Back.")
        # If external browser is running and user clicks Back on remote, close it and return to launcher
        if process_manager.is_running("external_browser"):
            await brave_service.close_external_browser()
            launcher_pid = process_manager.get_pid("launcher")
            if launcher_pid:
                restore_window_by_pid(launcher_pid)
            await state_manager.update(active_app="launcher")
            return {"status": "success", "action": "back_to_launcher"}

        input_service.send_key("ESCAPE")
        return {"status": "success", "action": "back"}

    async def exit_tv(self) -> dict:
        """Exits TV launcher only. Server and Remote remain online."""
        if mpv_service.is_running():
            await mpv_service.stop()
        await brave_service.close_external_browser()
        return await launcher_service.exit_launcher()

    async def reopen_tv(self) -> dict:
        """Reopens launcher on TV screen."""
        return await launcher_service.open_launcher()

app_controller = AppController()
