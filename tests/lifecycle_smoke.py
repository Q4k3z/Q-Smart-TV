import sys
import json
import time
import subprocess
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import psutil
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings, BASE_DIR
from scripts.server_identity import managed_server_process

BASE = f'http://127.0.0.1:{settings.PORT}'

def request(path, method='GET', body=None):
    req = urllib.request.Request(BASE + path, method=method,
        headers={'Authorization':f'Bearer {settings.AUTH_TOKEN}', 'Content-Type':'application/json'},
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def profile_pid(profile):
    expected = f'--user-data-dir={settings.DATA_DIR / profile}'.casefold()
    matches = []
    for proc in psutil.process_iter(['cmdline']):
        args = proc.info['cmdline'] or []
        if expected in [arg.casefold() for arg in args] and not any(a.startswith('--type=') for a in args):
            matches.append(proc.pid)
    assert len(matches) <= 1, f'Duplicate profile roots: {matches}'
    return matches[0] if matches else None

def wait_closed():
    for _ in range(30):
        if request('/api/status')['launcher'] == 'closed':
            return
        time.sleep(0.2)
    raise AssertionError('Manual window close did not update state')

assert request('/api/launcher/open','POST')['status'] in ('success','already_running')
original_pid = profile_pid('brave-tv-profile')
with ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(lambda _: request('/api/launcher/open','POST'), range(5)))
assert all(r['status'] == 'already_running' for r in results)
assert profile_pid('brave-tv-profile') == original_pid
old_server = managed_server_process()
assert old_server
stopped = subprocess.run([sys.executable, str(BASE_DIR / 'scripts/stop_server.py')], capture_output=True)
assert stopped.returncode == 0
assert psutil.pid_exists(original_pid), 'Stopping server closed launcher'
started = subprocess.run([sys.executable, str(BASE_DIR / 'scripts/start_smarttv.py')], capture_output=True, timeout=40)
assert started.returncode == 0, 'Restart failed; inspect startup.log'
assert managed_server_process().pid != old_server.pid
assert profile_pid('brave-tv-profile') == original_pid, 'Server restart duplicated the launcher'
# External browser remains alive when exiting the TV launcher.
existing_external = profile_pid('brave-external-profile')
if not existing_external:
    assert request('/api/browser/open','POST', {'url':BASE+'/health'})['status'] == 'success'
    time.sleep(2)
external_pid = profile_pid('brave-external-profile')
assert external_pid
assert request('/api/launcher/exit','POST')['status'] == 'success'
assert request('/health')['status'] == 'ok'
assert psutil.pid_exists(external_pid), 'Exit incorrectly closed external browser'
assert request('/api/launcher/open','POST')['status'] == 'success'
# Closing only the owned launcher process simulates a user closing its window.
manual_pid = profile_pid('brave-tv-profile')
psutil.Process(manual_pid).terminate()
wait_closed()
assert request('/health')['status'] == 'ok'
assert request('/api/launcher/open','POST')['status'] == 'success'
if not existing_external:
    proc = psutil.Process(external_pid)
    proc.terminate()
    proc.wait(timeout=5)
print('PASS: concurrent open, no duplicate launcher, server restart/adoption, exit isolation, manual-close detection, reopen; real Brave.')
