@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\configure_firewall.ps1"
if errorlevel 1 (
    echo [ERROR] Firewall was not configured. Read the message above.
    pause
    exit /b 1
)
pause
