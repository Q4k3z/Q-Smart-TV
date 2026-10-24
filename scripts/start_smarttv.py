import sys
import os
import time
import subprocess
import urllib.request
import json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from config import settings, get_lan_ip

def is_server_ready():
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{settings.PORT}/health")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False

def start_system():
    print("========================================================")
    print("          Q SMART TV — KHỞI CHẠY HỆ THỐNG")
    print("========================================================\n")

    # 1. Check or start FastAPI server
    if is_server_ready():
        print("[*] Server Q Smart TV đã đang hoạt động sẵn sàng.")
    else:
        print("[*] Đang khởi động FastAPI Server chạy nền...")
        server_py = str(root_dir / "server.py")
        log_file = settings.DATA_DIR / "logs" / "server_console.log"
        log_out = open(log_file, "a", encoding="utf-8")

        flags = subprocess.CREATE_NEW_PROCESS_GROUP
        if sys.platform == "win32":
            flags |= subprocess.DETACHED_PROCESS

        subprocess.Popen(
            [sys.executable, server_py],
            cwd=str(root_dir),
            stdout=log_out,
            stderr=log_out,
            creationflags=flags
        )

        ready = False
        for _ in range(15):
            time.sleep(1)
            if is_server_ready():
                ready = True
                break

        if not ready:
            print("[LỖI] Máy chủ không thể khởi động sau 15 giây.")
            print(f"Vui lòng kiểm tra log tại: {settings.DATA_DIR / 'logs' / 'server.log'}")
            input("Nhấn Enter để thoát...")
            sys.exit(1)
        print("[OK] Máy chủ FastAPI đã sẵn sàng.")

    # 2. Open TV Launcher
    print("[*] Đang mở giao diện TV Launcher trên màn hình...")
    open_url = f"http://127.0.0.1:{settings.PORT}/api/launcher/open?token={settings.AUTH_TOKEN}"
    try:
        req = urllib.request.Request(open_url, method="POST")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] {res_data.get('message', 'Đã gửi lệnh mở Launcher.')}")
    except Exception as e:
        print(f"[CẢNH BÁO] Không thể gọi API mở launcher: {e}")

    # 3. Print Remote Connection URL
    lan_ip = get_lan_ip()
    remote_url = f"http://{lan_ip}:{settings.PORT}/remote?token={settings.AUTH_TOKEN}"

    print("\n========================================================")
    print("  KẾT NỐI Q REMOTE TỪ ĐIỆN THOẠI (CÙNG WI-FI):")
    print(f"  {remote_url}")
    print("  (Hoặc quét mã QR trên góc phải màn hình TV)")
    print("========================================================\n")
    print("Hệ thống đang chạy. Để dừng máy chủ, chạy scripts\\stop_server.bat")
    time.sleep(3)

if __name__ == "__main__":
    start_system()
