import sys
import os
import socket
import urllib.request
import json
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from config import settings, get_lan_ip

def run_diagnostics():
    print("========================================================")
    print("          Q SMART TV — CHẨN ĐOÁN HỆ THỐNG")
    print("========================================================\n")

    # 1. Python version
    print("[1] Môi trường Python:")
    print(f"    Phiên bản: {sys.version.split()[0]}")
    print(f"    Thư mục gốc: {root_dir}")
    print("    -> Trạng thái: HỢP LỆ\n")

    # 2. Brave & mpv
    print("[2] Kiểm tra Brave Browser và mpv:")
    brave_ok = bool(settings.BRAVE_PATH and os.path.isfile(settings.BRAVE_PATH))
    mpv_ok = bool(settings.MPV_PATH and os.path.isfile(settings.MPV_PATH))
    print(f"    Brave: {settings.BRAVE_PATH if brave_ok else '[!] KHÔNG TÌM THẤY'}")
    print(f"    mpv:   {settings.MPV_PATH if mpv_ok else '[!] KHÔNG TÌM THẤY'}\n")

    # 3. Data Folders
    print("[3] Kiểm tra thư mục dữ liệu:")
    data_dir_ok = os.path.isdir(settings.DATA_DIR)
    print(f"    Thư mục data/: {'TỒN TẠI' if data_dir_ok else '[!] THIẾU'}")
    print(f"    Thư mục media: {len(settings.ALLOWED_MEDIA_DIRS)} thư mục được cấu hình")
    for d in settings.ALLOWED_MEDIA_DIRS:
        print(f"      - {d} ({'Tồn tại' if os.path.isdir(d) else 'Chưa có'})")
    print()

    # 4. Network and Port
    print("[4] Mạng nội bộ và Cổng kết nối:")
    lan_ip = get_lan_ip()
    print(f"    Địa chỉ IP LAN máy tính: {lan_ip}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    is_port_open = sock.connect_ex(("127.0.0.1", settings.PORT)) == 0
    sock.close()

    if is_port_open:
        print(f"    Cổng {settings.PORT}: Đang mở (Server Q Smart TV đang hoạt động)")
    else:
        print(f"    Cổng {settings.PORT}: Đang rảnh (Server chưa chạy)")
    print()

    # 5. Server Health
    print("[5] Trạng thái Health Server:")
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{settings.PORT}/health")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"    Server phản hồi: {data.get('status')} ({data.get('app')})")
    except Exception:
        print("    Server đang dừng (Offline)")

    print("\n========================================================")
    print("                 KẾT THÚC CHẨN ĐOÁN")
    print("========================================================")

if __name__ == "__main__":
    run_diagnostics()
