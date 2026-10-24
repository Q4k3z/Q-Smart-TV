@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo   Q SMART TV - DONG BO VA PUSH MA NGUON LEN GITHUB
echo ========================================================
echo.

:: 1. Kiem tra va bo sung Git vao PATH neu chua co
where git.exe >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"
    ) else if exist "C:\Program Files\Git\cmd\git.exe" (
        set "PATH=C:\Program Files\Git\cmd;%PATH%"
    ) else (
        echo [!] Khong tim thay Git. Vui long cai dat Git tu https://git-scm.com/
        pause
        exit /b 1
    )
)

:: 2. Kiem tra trang thai Git
echo [*] Dang kiem tra trang thai Git...
git status -s

echo.
echo [*] Dang them cac thay doi vao Git...
git add .

echo.
echo [*] Kiem tra commit moi...
git diff --cached --quiet
if %errorlevel% neq 0 (
    git commit -m "chore(release): update latest codebase, full documentation and project assets"
) else (
    echo [*] Khong co thay doi moi can commit.
)

:: 3. Day ma nguon len GitHub
echo.
echo [*] Dang push ma nguon len GitHub branch main...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   [THANH CONG] DU AN DA DUOC PUSH LEN GITHUB!
    echo   Dia chi Repository: https://github.com/Q4k3z/Q-Smart-TV
    echo ========================================================
) else (
    echo.
    echo [!] Co loi xay ra khi push len GitHub.
    echo [!] Vui long kiem tra quyen truy cap hoac ket noi mang cua ban.
)

echo.
pause
