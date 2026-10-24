@echo off
title Q Smart TV - Mo Khoa Tuong Lua Cho Dien Thoai
cd /d "%~dp0"

echo ========================================================
echo   Q SMART TV - MO KHOA KET NOI CHO DIEN THOAI (FIREWALL)
echo ========================================================
echo.
echo [*] Dang mo cong 8765 tren Tuong lua Windows...
echo [*] Vui long bam "Yes" tren hop thoai Windows UAC (neu co)...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process netsh -ArgumentList 'advfirewall firewall delete rule name=\"Q Smart TV Server\"' -Verb RunAs -Wait; Start-Process netsh -ArgumentList 'advfirewall firewall add rule name=\"Q Smart TV Server\" dir=in action=allow protocol=TCP localport=8765 profile=any' -Verb RunAs -Wait; Start-Process powershell -ArgumentList '-NoProfile -Command Get-NetConnectionProfile | Where-Object { $_.InterfaceAlias -like \"*Wi-Fi*\" -or $_.InterfaceAlias -like \"*Ethernet*\" } | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue' -Verb RunAs -Wait"

echo.
echo [*] Kiem tra ket qua Tuong lua:
netsh advfirewall firewall show rule name="Q Smart TV Server"
if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   [THANH CONG] DA MO KHOA TUONG LUA HOAN TAT!
    echo   Dien thoai bay gio da co the ket noi vao Q Remote.
    echo   Dia chi: http://192.168.1.7:8765
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo   [!] Neu chua hien thong tin Rule tren, ban hay:
    echo       1. Nhap CHUOT PHAI vao file 'mo_khoa_ket_noi.bat'
    echo       2. Chon: 'Run as administrator' (Chay voi quyen quan tri)
    echo ========================================================
)
echo.
pause
