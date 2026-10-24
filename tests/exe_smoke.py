"""Opt-in real quick-start EXE check. Restarts only this Q Smart TV server."""
import sys
import json
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import psutil
from config import BASE_DIR, settings
from scripts.server_identity import managed_server_process

EXE = BASE_DIR / 'Q Smart TV.exe'


def api(path, method='GET'):
    request = urllib.request.Request(f'http://127.0.0.1:{settings.PORT}'+path,
        method=method, headers={'Authorization':f'Bearer {settings.AUTH_TOKEN}'})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def launcher_pid():
    argument = f'--user-data-dir={settings.DATA_DIR / "brave-tv-profile"}'.casefold()
    roots = []
    for process in psutil.process_iter(['cmdline']):
        args = process.info['cmdline'] or []
        if argument in [arg.casefold() for arg in args] and not any(arg.startswith('--type=') for arg in args):
            roots.append(process.pid)
    assert len(roots) == 1, 'Expected one managed launcher process'
    return roots[0]


def launch():
    # Explorer shortcuts may start in any working directory.
    result = subprocess.run([str(EXE)], cwd=BASE_DIR/'.tmp', timeout=65)
    assert result.returncode == 0, 'Quick start failed; inspect data/logs/quickstart.log'


def run():
    assert EXE.is_file(), 'Build the EXE first'
    (BASE_DIR/'.tmp').mkdir(exist_ok=True)
    if managed_server_process():
        assert api('/api/launcher/exit', 'POST')['status'] == 'success'
    stopped = subprocess.run([sys.executable, str(BASE_DIR/'scripts/stop_server.py')], capture_output=True)
    assert stopped.returncode == 0
    launch()
    assert api('/health')['status'] == 'ok'
    assert api('/api/status')['launcher'] == 'open'
    server = managed_server_process()
    assert server
    original_launcher = launcher_pid()
    launch()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: launch(), range(4)))
    assert managed_server_process().pid == server.pid, 'Quick start duplicated the server'
    assert launcher_pid() == original_launcher, 'Quick start duplicated the launcher'
    log = (settings.DATA_DIR/'logs/quickstart.log').read_text(encoding='utf-8-sig')
    assert settings.AUTH_TOKEN not in log, 'Quick-start log must redact pairing credentials'
    assert api('/api/launcher/exit', 'POST')['status'] == 'success'
    assert api('/health')['status'] == 'ok', 'Exit TV closed the server'
    launch()
    assert api('/api/status')['launcher'] == 'open'
    assert managed_server_process().pid == server.pid
    print('PASS: EXE cold start, arbitrary working directory, warm/concurrent launch without duplicates, redacted log, exit/reopen; real Windows/Brave.')


if __name__ == '__main__':
    run()
