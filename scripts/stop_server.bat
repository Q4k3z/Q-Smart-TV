@echo off
cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\stop_server.py
) else (
    python scripts\stop_server.py
)
pause
