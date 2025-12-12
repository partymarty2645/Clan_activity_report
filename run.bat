@echo off
cd /d "%~dp0"
IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) ELSE (
    echo Virtual environment not found in .venv
    pause
)
pause
