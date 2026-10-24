@echo off
:: Q Smart TV - Mo Khoa Ket Noi Tuong Lua (Firewall)
cd /d "%~dp0"

:: Kiem tra quyen Administrator va tu dong yeu cau cap quyen neu can
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Dang yeu cau quyen Administrator de mo khoa Tuong lua (Firewall)...
    powershell -Command "Start-Process cmd -ArgumentList '/c `\"%~f0`\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   Q SMART TV - MO KHOA KET NOI CHO Q REMOTE
echo ========================================================
echo.
echo [*] Dang cap quyen Windows Firewall cho cong 8765 (Inbound TCP)...
netsh advfirewall firewall delete rule name="Q Smart TV Server" >nul 2>&1
netsh advfirewall firewall add rule name="Q Smart TV Server" dir=in action=allow protocol=TCP localport=8765 profile=any

echo.
echo [*] Dang chuyen mang Wi-Fi / Ethernet sang che do Private de ho tro ket noi LAN...
powershell -NoProfile -Command "Get-NetConnectionProfile | Where-Object { $_.InterfaceAlias -like '*Wi-Fi*' -or $_.InterfaceAlias -like '*Ethernet*' } | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue"

echo.
echo ========================================================
echo   [THANH CONG] DA MO KHOA HOAN TAT!
echo.
echo   - Dien thoai da co the ket noi vao Q Remote qua Wi-Fi.
echo   - Hay mo trinh duyet tren dien thoai hoac quet ma QR tren TV.
echo ========================================================
echo.
pause
