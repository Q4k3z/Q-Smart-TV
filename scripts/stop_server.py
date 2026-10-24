import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import psutil
from scripts.server_identity import managed_server_process, IDENTITY_FILE


def stop_server():
    proc = managed_server_process()
    if not proc:
        print('[!] Không tìm thấy server thuộc Q Smart TV này. Không đóng tiến trình khác.')
        return 0
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        IDENTITY_FILE.unlink(missing_ok=True)
        print('[OK] Đã dừng server Q Smart TV.')
        return 0
    except psutil.Error:
        print('[LỖI] Không thể dừng server. Kiểm tra quyền của tiến trình.')
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(stop_server())
