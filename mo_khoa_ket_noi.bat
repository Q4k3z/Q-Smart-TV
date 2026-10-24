@echo off
cd /d "%~dp0"

if "%~1"=="elevated" goto :run_admin

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ========================================================
    echo   Q SMART TV - MO KHOA KET NOI CHO DIEN THOAI (FIREWALL)
    echo ========================================================
    echo.
    echo [*] Dang yeu cau quyen Administrator...
    echo [*] Vui long bam "Yes" (Co) khi Windows hien bang xac nhan UAC.
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c `\"%~f0`\" elevated' -Verb RunAs"
    exit /b
)

:run_admin
echo ========================================================
echo   Q SMART TV - DANG MO KHOA TUONG LUA (ADMINISTRATOR)
echo ========================================================
echo.

echo [*] Dang tao quy tac cho phep cong 8765 tren Windows Firewall...
netsh advfirewall firewall delete rule name="Q Smart TV Server" >nul 2>&1
netsh advfirewall firewall add rule name="Q Smart TV Server" dir=in action=allow protocol=TCP localport=8765 profile=any

echo [*] Dang chuyen Wi-Fi sang che do Private (Ho tro ket noi mang noi bo)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetConnectionProfile | Where-Object { $_.InterfaceAlias -like '*Wi-Fi*' -or $_.InterfaceAlias -like '*Ethernet*' } | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\configure_firewall.ps1"

echo.
echo ========================================================
echo   [THANH CONG] DA MO KHOA HOAN TAT!
echo   Dien thoai bay gio da co the ket noi vao Q Remote.
echo   Dia chi: http://192.168.1.7:8765
echo ========================================================
echo.
pause
