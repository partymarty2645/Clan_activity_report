@echo off
TITLE WOM Clan Report - Auto Run
cd /d "%~dp0"
IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) ELSE (
    echo Virtual environment not found in .venv
    exit /b 1
)
pause
