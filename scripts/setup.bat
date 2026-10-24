@echo off
cd /d "%~dp0\.."

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found on system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating Python virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create .venv virtual environment.
        pause
        exit /b 1
    )
)

.\.venv\Scripts\python.exe scripts\setup.py
pause
