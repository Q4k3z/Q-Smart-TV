import sys
import os
import subprocess
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

def run_setup():
    print("========================================================")
    print("       Q SMART TV — THIẾT LẬP MÔI TRƯỜNG TỰ ĐỘNG")
    print("========================================================\n")

    # 1. Check Python
    print(f"[*] Phiên bản Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("[LỖI] Yêu cầu Python 3.10 trở lên.")
        input("Nhấn Enter để thoát...")
        sys.exit(1)

    # 2. Check requirements
    req_file = root_dir / "requirements.txt"
    if req_file.is_file():
        print("[*] Đang kiểm tra và cài đặt thư viện phụ thuộc...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
            print("[OK] Cài đặt thư viện thành công.\n")
        except subprocess.CalledProcessError as e:
            print(f"[LỖI] Không thể cài đặt dependencies: {e}")
            input("Nhấn Enter để thoát...")
            sys.exit(1)

    # 3. Import config to ensure folders and token
    import config
    print("[*] Kiểm tra cấu hình và dữ liệu:")
    print(f"    Thư mục data:  {config.settings.DATA_DIR}")
    print(f"    Thư mục media: {config.settings.DATA_DIR / 'media'}")
    print(f"    Brave Browser: {config.settings.BRAVE_PATH or '[!] CHƯA TÌM THẤY'}")
    print(f"    mpv Player:    {config.settings.MPV_PATH or '[!] CHƯA TÌM THẤY'}\n")
    if not config.settings.BRAVE_PATH:
        print("[!] Cần cài Brave từ https://brave.com/download/ để mở launcher.")
    if not config.settings.MPV_PATH:
        print("[!] Chưa phát được media/IPTV. Cài mpv theo https://mpv.io/installation/ và đặt QSMART_MPV_PATH trong .env.")

    print("========================================================")
    print("       HOÀN THÀNH CÀI ĐẶT Q SMART TV THÀNH CÔNG!")
    print("========================================================")
    print("Bạn có thể khởi động hệ thống bằng: scripts\\start_smarttv.bat\n")

if __name__ == "__main__":
    run_setup()
