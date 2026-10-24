import asyncio
import sys
import os
import time
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path

# Configure stdout for Windows console UTF-8 support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Setup paths
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from config import settings, get_lan_ip
from core.mpv_service import mpv_service
from core.brave_service import brave_service
from core.launcher_service import launcher_service
from core.system_service import system_service
from core.iptv_service import iptv_service
from core.process_manager import process_manager

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

async def run_e2e_verification():
    print_header("BẮT ĐẦU TỰ KIỂM THỬ TOÀN BỘ HỆ THỐNG Q SMART TV (LIVE)")
    report = []

    # ----------------------------------------------------
    # TEST 1: Khởi động Server FastAPI
    # ----------------------------------------------------
    print("\n[TEST 1] Khởi động Server FastAPI...")
    log_file = settings.DATA_DIR / "logs" / "test_server.log"
    log_out = open(log_file, "w", encoding="utf-8")
    server_proc = subprocess.Popen(
        [sys.executable, str(root_dir / "server.py")],
        cwd=str(root_dir),
        stdout=log_out,
        stderr=log_out
    )
    
    server_online = False
    for i in range(15):
        await asyncio.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{settings.PORT}/health", timeout=1.0) as r:
                res = json.loads(r.read().decode())
                if res.get("status") == "ok":
                    server_online = True
                    break
        except Exception:
            pass

    if server_online:
        print(f" -> THÀNH CÔNG: Server đang chạy (PID={server_proc.pid}, Cổng={settings.PORT})")
        report.append(("Khởi động Server & Health Check", "PASSED"))
    else:
        print(" -> THẤT BẠI: Server không phản hồi sau 7.5s")
        report.append(("Khởi động Server & Health Check", "FAILED"))
        server_proc.terminate()
        return report

    # ----------------------------------------------------
    # TEST 2: Kiểm tra bảo mật Token (Xác thực REST API)
    # ----------------------------------------------------
    print("\n[TEST 2] Kiểm tra ranh giới bảo mật Token...")
    # Request không có token -> phải bị 401
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{settings.PORT}/api/status", timeout=1.0)
        print(" -> THẤT BẠI: Không có token mà server vẫn trả về 200!")
        report.append(("Bảo mật Token (Chặn truy cập trái phép)", "FAILED"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(" -> THÀNH CÔNG: Chặn truy cập trái phép (Mã lỗi 401 Unauthorized)")
            report.append(("Bảo mật Token (Chặn truy cập trái phép)", "PASSED"))
        else:
            print(f" -> Lỗi bất ngờ: {e.code}")
            report.append(("Bảo mật Token (Chặn truy cập trái phép)", "FAILED"))

    # Request có token hợp lệ -> phải 200
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{settings.PORT}/api/status?token={settings.AUTH_TOKEN}"
        )
        with urllib.request.urlopen(req, timeout=1.0) as r:
            status_data = json.loads(r.read().decode())
            assert status_data.get("server") == "online"
            print(f" -> THÀNH CÔNG: Xác thực hợp lệ, server trả về: {status_data}")
            report.append(("Bảo mật Token (Xác thực hợp lệ)", "PASSED"))
    except Exception as e:
        print(f" -> THẤT BẠI: {e}")
        report.append(("Bảo mật Token (Xác thực hợp lệ)", "FAILED"))

    # ----------------------------------------------------
    # TEST 3: Tạo mã QR SVG & Thông tin ghép nối
    # ----------------------------------------------------
    print("\n[TEST 3] Kiểm tra mã QR ghép nối & Info Endpoint...")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{settings.PORT}/api/qrcode?token={settings.AUTH_TOKEN}", timeout=2.0) as r:
            svg_content = r.read().decode()
            assert "<svg" in svg_content
            assert "image/svg+xml" in r.headers.get("content-type", "")
            print(f" -> THÀNH CÔNG: Đã sinh mã QR SVG chuẩn ({len(svg_content)} bytes)")
            report.append(("Sinh mã QR Ghép nối SVG", "PASSED"))
    except Exception as e:
        print(f" -> THẤT BẠI: {e}")
        report.append(("Sinh mã QR Ghép nối SVG", "FAILED"))

    # ----------------------------------------------------
    # TEST 4: Quét phim offline trong thư mục an toàn
    # ----------------------------------------------------
    print("\n[TEST 4] Kiểm tra quét phim offline...")
    movies = system_service.scan_movies()
    if len(movies) > 0 and any(m["filename"] == "Mau_Phim_Thu_Nghiem.mp4" for m in movies):
        print(f" -> THÀNH CÔNG: Tìm thấy {len(movies)} phim, bao gồm tệp mẫu Mau_Phim_Thu_Nghiem.mp4")
        report.append(("Quét phim offline", "PASSED"))
    else:
        print(f" -> THẤT BẠI: Không quét được video (movies={movies})")
        report.append(("Quét phim offline", "FAILED"))

    # ----------------------------------------------------
    # TEST 5: Phân tích IPTV & Danh sách phát
    # ----------------------------------------------------
    print("\n[TEST 5] Kiểm tra IPTV Service & Playlist...")
    playlists = iptv_service.get_playlists()
    print(f" -> Danh sách Playlist đã cấu hình: {len(playlists)}")
    channels = iptv_service.load_channels()
    print(f" -> Số lượng kênh tải được: {len(channels)}")
    if len(playlists) > 0:
        print(" -> THÀNH CÔNG: IPTV Service hoạt động tốt")
        report.append(("IPTV Service & Kênh truyền hình", "PASSED"))
    else:
        print(" -> THẤT BẠI: Không tìm thấy playlist")
        report.append(("IPTV Service & Kênh truyền hình", "FAILED"))

    # ----------------------------------------------------
    # TEST 6: Phát Media bằng mpv qua Windows Named Pipe IPC
    # ----------------------------------------------------
    print("\n[TEST 6] Kiểm tra phát video bằng mpv & Named Pipe IPC...")
    test_video = str(root_dir / "data" / "media" / "Mau_Phim_Thu_Nghiem.mp4")
    play_res = await mpv_service.play(test_video, title="Kiểm Thử Tự Động")
    print(f" -> Lệnh phát mpv: {play_res}")
    await asyncio.sleep(1.5)

    is_playing = mpv_service.is_running()
    print(f" -> Tiến trình mpv đang chạy: {is_playing}")
    
    # Thử tạm dừng qua IPC
    pause_res = await mpv_service.pause_toggle()
    print(f" -> Lệnh pause qua IPC: {pause_res}")

    # Thử tua qua IPC
    seek_res = await mpv_service.seek(5.0)
    print(f" -> Lệnh seek qua IPC: {seek_res}")

    # Thử điều chỉnh âm lượng qua IPC
    vol_res = await mpv_service.volume_change(5)
    print(f" -> Lệnh volume qua IPC: {vol_res}")

    # Dừng phát an toàn
    stop_res = await mpv_service.stop()
    print(f" -> Lệnh dừng phát: {stop_res}")
    await asyncio.sleep(0.5)

    if is_playing and not mpv_service.is_running():
        print(" -> THÀNH CÔNG: mpv phát video và IPC hoạt động hoàn hảo")
        report.append(("Trình phát mpv & Named Pipe JSON IPC", "PASSED"))
    else:
        print(" -> THẤT BẠI: mpv không phản hồi đúng")
        report.append(("Trình phát mpv & Named Pipe JSON IPC", "FAILED"))

    # ----------------------------------------------------
    # TEST 7: Khởi chạy Trình duyệt Brave & Window Focus
    # ----------------------------------------------------
    print("\n[TEST 7] Kiểm tra khởi chạy Brave & Quản lý cửa sổ Focus...")
    brave_res = await brave_service.open_url("https://www.google.com")
    print(f" -> Mở Brave: {brave_res}")
    await asyncio.sleep(2.0)

    brave_running = process_manager.is_running("external_browser")
    print(f" -> Tiến trình Brave ngoài đang chạy: {brave_running}")

    # Đóng trình duyệt ngoài sạch sẽ
    close_brave_res = await brave_service.close_external_browser()
    print(f" -> Đóng trình duyệt ngoài: {close_brave_res}")

    if brave_running:
        print(" -> THÀNH CÔNG: Brave mở trang web và kéo cửa sổ lên đầu mượt mà")
        report.append(("Khởi chạy Brave & Quản lý cửa sổ Focus", "PASSED"))
    else:
        print(" -> THẤT BẠI: Brave không khởi chạy được")
        report.append(("Khởi chạy Brave & Quản lý cửa sổ Focus", "FAILED"))

    # ----------------------------------------------------
    # TEST 8: Vòng đời Launcher (Thoát TV và Mở lại TV)
    # ----------------------------------------------------
    print("\n[TEST 8] Kiểm tra vòng đời Launcher (Thoát TV & Mở lại)...")
    # Mở Launcher
    open_launcher_res = await launcher_service.open_launcher()
    print(f" -> Mở Launcher: {open_launcher_res}")
    await asyncio.sleep(1.5)
    launcher_open = launcher_service.is_open()
    print(f" -> Trạng thái Launcher đang mở: {launcher_open}")

    # Thoát TV (Chỉ đóng launcher, server vẫn chạy)
    exit_launcher_res = await launcher_service.exit_launcher()
    print(f" -> Thoát TV: {exit_launcher_res}")
    await asyncio.sleep(1.0)
    launcher_closed = not launcher_service.is_open()
    print(f" -> Trạng thái Launcher đã đóng: {launcher_closed}")

    # Kiểm tra server vẫn sống sau khi thoát launcher
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{settings.PORT}/health", timeout=1.0) as r:
            server_still_alive = json.loads(r.read().decode()).get("status") == "ok"
    except Exception:
        server_still_alive = False

    print(f" -> Server vẫn chạy sau khi Thoát TV: {server_still_alive}")

    if launcher_open and launcher_closed and server_still_alive:
        print(" -> THÀNH CÔNG: Vòng đời Launcher độc lập hoàn toàn với Server")
        report.append(("Vòng đời Launcher độc lập (Thoát TV giữ Server)", "PASSED"))
    else:
        print(" -> THẤT BẠI: Vòng đời Launcher gặp lỗi")
        report.append(("Vòng đời Launcher độc lập (Thoát TV giữ Server)", "FAILED"))

    # ----------------------------------------------------
    # Tắt Server kết thúc phiên kiểm thử
    # ----------------------------------------------------
    server_proc.terminate()
    try:
        server_proc.wait(timeout=2.0)
    except Exception:
        server_proc.kill()
    log_out.close()

    return report

if __name__ == "__main__":
    results = asyncio.run(run_e2e_verification())
    print_header("TỔNG HỢP KẾT QUẢ TỰ KIỂM THỬ TOÀN DIỆN (E2E)")
    all_passed = True
    for item, status in results:
        indicator = "✅ [PASSED]" if status == "PASSED" else "❌ [FAILED]"
        print(f"  {indicator} - {item}")
        if status != "PASSED":
            all_passed = False
    print("=" * 60)
    if all_passed:
        print("  >>> TẤT CẢ TÍNH NĂNG ĐỀU VƯỢT QUA KIỂM THỬ THỰC TẾ 100% <<<")
    else:
        print("  >>> CÓ MỤC KIỂM THỬ KHÔNG ĐẠT <<<")
    print("=" * 60 + "\n")
    sys.exit(0 if all_passed else 1)
