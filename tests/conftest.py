import os
import tempfile
from pathlib import Path
import pytest

# Tests must never write personal playlists, credentials, or process identity.
test_root = Path(__file__).resolve().parent.parent / '.tmp'
test_root.mkdir(exist_ok=True)
os.environ['QSMART_DATA_DIR'] = tempfile.mkdtemp(prefix='pytest-data-', dir=test_root)
os.environ['QSMART_AUTH_TOKEN'] = 'test-only-token-not-a-real-credential'


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    from core.state_manager import state_manager
    from core.event_bus import event_bus
    from core.process_manager import process_manager
    from core.input_service import input_service
    state_manager.launcher = 'closed'
    state_manager.active_app = None
    state_manager.mpv = 'stopped'
    state_manager.current_media = None
    event_bus._subscribers.clear()
    event_bus._tv_subscribers.clear()
    process_manager._processes.clear()
    # Unmocked real key injection would affect the user's current window.
    monkeypatch.setattr(input_service, '_focus_target', lambda target: False)
