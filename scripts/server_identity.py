import json
import os
from pathlib import Path
import psutil
from config import settings, BASE_DIR

IDENTITY_FILE = settings.DATA_DIR / 'config' / 'server_process.json'
SERVER_PATH = str((BASE_DIR / 'server.py').resolve())


def save_server_identity():
    proc = psutil.Process(os.getpid())
    IDENTITY_FILE.write_text(json.dumps({'pid': proc.pid, 'created': proc.create_time(), 'script': SERVER_PATH}), encoding='utf-8')


def managed_server_process():
    try:
        data = json.loads(IDENTITY_FILE.read_text(encoding='utf-8'))
        proc = psutil.Process(data['pid'])
        if abs(proc.create_time() - data['created']) > 0.01 or data['script'] != SERVER_PATH:
            return None
        args = proc.cmdline()[1:]
        if not any(str(Path(arg).resolve()).casefold() == SERVER_PATH.casefold() for arg in args):
            return None
        return proc
    except (OSError, ValueError, KeyError, psutil.Error):
        return None
