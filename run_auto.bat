@echo off
TITLE WOM Clan Report - Auto Run
cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found in .venv
    echo Please run setup.bat first.
    pause
    exit /b 1
)


echo Running Database Backup...
".venv\Scripts\python.exe" scripts/backup_db.py
if errorlevel 1 (
    echo WARNING: Database backup failed. Continuing...
)

echo Running Weekly Database Optimization Check...
".venv\Scripts\python.exe" scripts/optimize_database.py
if errorlevel 1 (
    echo WARNING: Database optimization failed. Stopping execution to prevent corruption.
    goto error
)
REM Note: Removed --check-weekly flag if not supported by new script, or ensure script supports it.

echo Running Orchestrator...
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto error

echo Generating Weekly Clan Spotlight (Fun Stats)...
".venv\Scripts\python.exe" reporting/fun_stats_sqlite.py

if errorlevel 1 (
    echo WARNING: Fun Stats Analysis failed. Continuing...
)


echo ========================================
echo SUCCESS: Report generated successfully.
echo ========================================
goto end

:error
echo.
echo ========================================
echo FAILURE: An error occurred during execution.
echo Check app.log for details.
echo ========================================
pause
exit /b 1

:end
pause
