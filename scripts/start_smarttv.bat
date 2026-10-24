@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [LỖI] Môi trường chưa được cài đặt. Hãy chạy setup.bat trước!
    pause
    exit /b 1
)

.\.venv\Scripts\python.exe scripts\start_smarttv.py
