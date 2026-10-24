@echo off
chcp 65001 >nul
echo ========================================================
echo       Q SMART TV — THIẾT LẬP MÔI TRƯỜNG TỰ ĐỘNG
echo ========================================================

cd /d "%~dp0\.."

REM 1. Kiểm tra Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trên máy tính!
    echo Vui lòng cài đặt Python 3.10 trở lên từ https://www.python.org/
    pause
    exit /b 1
)

REM 2. Tạo virtual environment nếu chưa có
if not exist ".venv" (
    echo [*] Đang khởi tạo môi trường Python ảo (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [LỖI] Không thể tạo virtual environment.
        pause
        exit /b 1
    )
)

REM 3. Cài đặt các thư viện phụ thuộc
echo [*] Đang cài đặt thư viện từ requirements.txt...
.\.venv\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo [LỖI] Không thể cài đặt các thư viện cần thiết.
    pause
    exit /b 1
)

REM 4. Khởi tạo các thư mục dữ liệu và cấu hình
echo [*] Kiểm tra thư mục dữ liệu và cấu hình...
.\.venv\Scripts\python.exe -c "import config; print('Dữ liệu sẵn sàng tại:', config.settings.DATA_DIR)"

REM 5. Kiểm tra Brave và mpv
echo [*] Đang kiểm tra Brave Browser và mpv...
.\.venv\Scripts\python.exe -c "import config; print('Brave:', config.settings.BRAVE_PATH or 'CHƯA TÌM THẤY'); print('mpv:  ', config.settings.MPV_PATH or 'CHƯA TÌM THẤY')"

echo.
echo ========================================================
echo       HOÀN THÀNH CÀI ĐẶT Q SMART TV THÀNH CÔNG!
echo ========================================================
echo Bạn có thể khởi động hệ thống bằng file: scripts\start_smarttv.bat
echo.
pause
