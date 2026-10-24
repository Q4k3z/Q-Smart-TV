@echo off
cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\diagnose.py
) else (
    python scripts\diagnose.py
)
pause
