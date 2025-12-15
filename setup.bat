@echo off
TITLE WOM Clan Stats - First Time Setup
echo ===================================================
echo      WOM Discord MVP - Initial Setup Wizard
echo ===================================================
echo.

:: 1. Find Python executable (supports py, python, python3) - Checks Execution, not just path
set "PY_EXEC="

:: Try 'py' launcher first (standard on Windows)
py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 set "PY_EXEC=py -3" & goto :PY_FOUND

:: Try 'python' (fallback, checks if it actually runs to avoid broken Store shims)
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 set "PY_EXEC=python" & goto :PY_FOUND

:: Try 'python3' (fallback for some systems)
python3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 set "PY_EXEC=python3" & goto :PY_FOUND
echo [ERROR] Did not find a usable Python 3 executable (python, py, python3).
echo Please install Python 3.10+ from https://www.python.org/downloads/ and ensure the installer option to add Python to PATH is enabled.
echo Alternatively, install the 'py' launcher (usually included) and try running this script again.
pause
exit /b 1

:PY_FOUND
echo [INFO] Using Python: %PY_EXEC%

:: 2. Create or repair Virtual Environment
if not exist ".venv\" (
    echo [1/3] Creating virtual environment .venv using %PY_EXEC%...
    %PY_EXEC% -m venv .venv
) else (
    echo [1/3] Virtual environment already exists. Verifying...
    ".venv\Scripts\python.exe" --version >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo [WARN] Existing .venv appears broken. Recreating...
        rmdir /s /q .venv
        %PY_EXEC% -m venv .venv
    ) else (
        echo [1/3] .venv OK.
    )
)

:: 3. Install Dependencies
echo [2/3] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo [WARN] Installing requirements failed. Attempting to recreate virtualenv and retry...
    rmdir /s /q .venv
    %PY_EXEC% -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install requirements after recreating venv.
        pause
        exit /b 1
    )
)

:: 4. Check .env
if not exist ".env" (
    echo [3/3] Creating .env file from template...
    echo # --- Discord Configuration --- > .env
    echo # Bot Token (From Developer Portal -> Bot -> Reset Token) >> .env
    echo # IMPORTANT: Enable "Message Content Intent" in the Bot tab! >> .env
    echo DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE >> .env
    echo RELAY_CHANNEL_ID= >> .env
    echo. >> .env
    echo # --- Wise Old Man Configuration --- >> .env
    echo WOM_API_KEY=YOUR_KEY_HERE >> .env
    echo WOM_GROUP_ID= >> .env
    echo WOM_GROUP_SECRET= >> .env
    echo. >> .env
    echo # --- Settings --- >> .env
    echo CUSTOM_START_DATE=2025-02-14 >> .env
    echo. >> .env
    echo # --- Google Drive (Optional) --- >> .env
    echo # Folder ID where reports will be uploaded >> .env
    echo GOOGLE_DRIVE_FOLDER_ID= >> .env
    echo. >> .env
    echo [WARN] A new .env file was created. You MUST edit it with your keys!
) else (
    echo [3/3] .env file found. Preserving existing settings.
)

:: 5. Check for Drive Path (Optional)
if not exist "G:\" (
    echo.
    echo [INFO] G: Drive not found. 
    echo If you use Google Drive Desktop, make sure it is running 
    echo if you want to use LOCAL_DRIVE_PATH.
)

echo.
echo ===================================================
echo [SUCCESS] Setup Complete!
echo.
echo 1. Open ".env" and add your API keys.
echo 2. Double-click "run_auto.bat" to start the bot.
echo ===================================================
pause
