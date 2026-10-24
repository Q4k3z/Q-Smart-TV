@echo off
cd /d "%~dp0"

echo ========================================================
echo   Q SMART TV - PUSH DU AN LEN GITHUB (PUBLIC)
echo ========================================================
echo.

set "GH_EXE=C:\Program Files\GitHub CLI\gh.exe"
if not exist "%GH_EXE%" (
    set "GH_EXE=gh"
)

:: 1. Kiem tra xac thuc GitHub
"%GH_EXE%" auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Ban chua dang nhap GitHub tren may tinh.
    echo [*] He thong se mo trinh duyet de xac thuc GitHub (Dang nhap 1 lan duy nhat)...
    echo.
    "%GH_EXE%" auth login -h github.com -p https -w
)

echo.
echo [*] Dang tao va day ma nguon len GitHub Q4k3z/Q-Smart-TV (Public)...
"%GH_EXE%" repo create Q-Smart-TV --public --source=. --remote=origin --push >nul 2>&1

if %errorlevel% neq 0 (
    echo [*] Repository da ton tai hoac can dong bo, dang thuc hien git push...
    git push -u origin main
)

echo.
echo ========================================================
echo   [THANH CONG] DU AN DA DUOC PUSH LEN GITHUB!
echo   Dia chi Repository: https://github.com/Q4k3z/Q-Smart-TV
echo ========================================================
echo.
pause
