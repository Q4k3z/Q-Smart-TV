import sys
import psutil

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def stop_server():
    print("========================================================")
    print("          Q SMART TV — DỪNG MÁY CHỦ SERVER")
    print("========================================================\n")

    stopped_count = 0
    # Search for processes listening on port 8765
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == 8765:
            pid = conn.pid
            if pid and pid != psutil.Process().pid:
                try:
                    proc = psutil.Process(pid)
                    p_name = proc.name()
                    proc.terminate()
                    gone, alive = psutil.wait_procs([proc], timeout=3.0)
                    if alive:
                        proc.kill()
                    print(f"[*] Đã dừng máy chủ: PID={pid} ({p_name})")
                    stopped_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    if stopped_count > 0:
        print(f"\n[OK] Đã dừng thành công {stopped_count} tiến trình máy chủ Q Smart TV.")
    else:
        print("[!] Không tìm thấy máy chủ Q Smart TV đang lắng nghe trên cổng 8765.")

if __name__ == "__main__":
    stop_server()
