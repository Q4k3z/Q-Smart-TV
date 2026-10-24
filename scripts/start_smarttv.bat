@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
    call scripts\setup.bat
    if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -c "import fastapi, uvicorn, pydantic_settings, psutil, qrcode" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Dependencies missing. Run setup.bat and try again.
    pause
    exit /b 1
)
.venv\Scripts\python.exe scripts\start_smarttv.py
if errorlevel 1 (
    echo [ERROR] Q Smart TV could not open. The server may still be running.
    pause
    exit /b 1
)
exit /b 0
