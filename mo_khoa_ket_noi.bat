@echo off
:: Self-elevate to Administrator if not already elevated
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Dang yeu cau quyen Administrator de cau hinh Tuong lua (Firewall)...
    powershell -Command "Start-Process cmd -ArgumentList '/c `\"%~f0`\"' -Verb RunAs"
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\configure_firewall.ps1"
if errorlevel 1 (
    echo [ERROR] Firewall was not configured. Read the message above.
    pause
    exit /b 1
)
pause
