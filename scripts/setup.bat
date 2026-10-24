@echo off
setlocal
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" goto install
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if not errorlevel 1 (
    py -3 -m venv .venv
    goto check
)
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Install Python 3.10+ from https://www.python.org/downloads/windows/
    echo Enable the Python launcher or add Python to PATH, then run setup.bat again.
    pause
    exit /b 1
)
python -m venv .venv
:check
if errorlevel 1 goto failed
:install
.venv\Scripts\python.exe -m pip --version >nul 2>nul
if errorlevel 1 .venv\Scripts\python.exe -m ensurepip --upgrade
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\setup.py
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo [ERROR] Setup failed. Read the error above.
pause
exit /b 1
