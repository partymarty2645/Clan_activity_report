@echo off
TITLE WOM Clan Stats - First Time Setup
echo ===================================================
echo      WOM Discord MVP - Initial Setup Wizard
echo ===================================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from python.org and tick "Add to PATH".
    pause
    exit /b 1
)

:: 2. Create Virtual Environment
if not exist ".venv\" (
    echo [1/3] Creating virtual environment .venv...
    python -m venv .venv
) else (
    echo [1/3] Virtual environment already exists.
)

:: 3. Install Dependencies
echo [2/3] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
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
