import sys
import time
import subprocess
import urllib.request
import urllib.error
import json
import socket
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
from config import settings, get_lan_ip
from scripts.server_identity import managed_server_process


def check_firewall():
    if sys.platform != 'win32':
        return
    try:
        check = subprocess.run(['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=Q Smart TV Server'],
                               capture_output=True, text=True)
        if 'Q Smart TV Server' not in check.stdout:
            print('[*] Phat hien Tuong lua chua mo cong 8765 cho dien thoai.')
            print('[*] Dang yeu cau mo Tuong lua (vui long chon Yes neu hien bang UAC)...')
            bat = str(root_dir / 'mo_khoa_ket_noi.bat')
            subprocess.run(['powershell', '-NoProfile', '-Command', f"Start-Process -FilePath '{bat}' -Verb RunAs"])
    except Exception:
        pass


def is_server_ready():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{settings.PORT}/health', timeout=1) as resp:
            return json.load(resp) == {'status': 'ok', 'app': 'Q Smart TV'}
    except (OSError, ValueError):
        return False


def start_system():
    check_firewall()
    if is_server_ready():
        if not managed_server_process():
            print('[LỖI] Cổng đang thuộc một server khác. Kiểm tra QSMART_PORT; không mở thêm server.')
            return 1
        print('[OK] Server Q Smart TV đã chạy.')
    else:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1', settings.PORT)) == 0:
                print(f'[LỖI] Cổng {settings.PORT} bị ứng dụng khác chiếm. Đổi QSMART_PORT trong .env.')
                return 1
        log_path = settings.DATA_DIR / 'logs' / 'startup.log'
        flags = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS) if sys.platform == 'win32' else 0
        with log_path.open('a', encoding='utf-8') as log:
            proc = subprocess.Popen([sys.executable, str(root_dir / 'server.py')], cwd=root_dir,
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=flags)
        for _ in range(40):
            if is_server_ready():
                break
            if proc.poll() is not None:
                break
            time.sleep(0.5)
        if not is_server_ready():
            print(f'[LỖI] Server chưa sẵn sàng. Xem {log_path}')
            return 1
    req = urllib.request.Request(f'http://127.0.0.1:{settings.PORT}/api/launcher/open', method='POST',
                                 headers={'Authorization': f'Bearer {settings.AUTH_TOKEN}'})
    result = None
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.load(resp)
        print(result.get('message', ''))
    except (OSError, ValueError):
        print('[LỖI] Không gọi được launcher. Xem data/logs/server.log; server vẫn chạy.')
    print(f'Q Remote: http://{get_lan_ip()}:{settings.PORT}/remote?token={settings.AUTH_TOKEN}')
    print('Điện thoại dùng cùng Wi-Fi. Nếu bị chặn, xem diagnose.bat và hướng dẫn Firewall trong README.')
    return 0 if result and result.get('status') in ('success', 'already_running') else 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    # Serialize double-clicks without requiring an extra dependency or administrator.
    import msvcrt
    with (settings.DATA_DIR / 'config' / 'startup.lock').open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            print('Q Smart TV đang khởi động. Vui lòng đợi.')
            sys.exit(0)
        sys.exit(start_system())
