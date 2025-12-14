# WomDiscordMVP: Clan Statistics & Tracking

A robust tool for tracking Old School RuneScape (OSRS) clan statistics by integrating **Wise Old Man (WOM)** data with **Discord** activity.

## 🚀 Key Features

-   **Discord Integration**: accurately tracks message counts and discussion topics for clan members.
-   **Smart Data Fetching**:
    -   **Lazy Sync**: Only fetches fresh data from Wise Old Man once per day per user to respect API limits.
    -   **Name Change Detection**: Automatically detects when members change their OSRS names and updates history.
-   **Comprehensive Reporting**:
    -   **Excel & CSV**: Generates detailed spreadsheets with specific timeframes (7d, 30d, 70d, 150d, Total).
    -   **Text Analysis**: Includes "Favorite Word" and "Question Count" (30d) for each member.
    -   **Visuals**: Color-coded columns, auto-sizing, and frozen headers for easy reading.
-   **Automated Sync**:
    -   **Google Drive**: Can automatically copy the latest report to your Google Drive folder.
    -   **Resilience**: Handles file permission errors (if Excel is open) by creating backups.

---

## 📦 Fresh Installation (New System)

Follow these steps to set up the project on a new computer.

### 1. Install Prerequisites
-   **Python 3.10+**: Download from [python.org](https://www.python.org/).
    -   ⚠️ **IMPORTANT**: Check **"Add Python to PATH"** during installation.
-   **Git**: Download from [git-scm.com](https://git-scm.com/).

### 2. Get the Code
Open a terminal (Command Prompt) and run:
```bash
git clone https://github.com/partymarty2645/clanstats.git
cd clanstats
```

### 3. One-Click Setup
Double-click **`setup.bat`**.
This will:
1.  Verify Python installation.
2.  Create a virtual environment (`.venv`).
3.  Install dependencies.
4.  Create a `.env` file if missing.

### 4. Configure Keys (`.env`)
Open `.env` with a text editor:
```ini
# --- Discord Configuration ---
DISCORD_TOKEN=your_bot_token_here
RELAY_CHANNEL_ID=1234567890

# --- Wise Old Man Configuration ---
WOM_API_KEY=your_wom_api_key
WOM_GROUP_ID=11114
WOM_GROUP_SECRET=your_group_security_code

# --- Settings ---
# Start date for "Total" stats
CUSTOM_START_DATE=2025-02-14

# Safe test mode (True = Limit fetch to 5 players, no waiting)
WOM_TEST_MODE=False

# --- Google Drive (Local Sync) ---
# Path to your G: Drive folder to auto-copy reports
LOCAL_DRIVE_PATH=G:\My Drive\Shared_clan_data\Excel_sheet
```

---

## 🏃 Running the Bot

### Automatic (Recommended)
Double-click **`run_auto.bat`**.
-   Updates WOM group data.
-   Syncs Discord messages.
-   Fetches player snapshots (or loads from local cache).
-   Generates `clan_report_summary_merged.xlsx`.
-   Copies to Google Drive (if configured).

### Deep Dive: Word Analysis
To run a standalone text frequency analysis (generating `words_report.txt`):
```bash
.\.venv\Scripts\activate
python analyze_words.py
```

---

## 📂 Troubleshooting

-   **"File Permission Error"**: You likely have the Excel file open. Close it and try again. The script will attempt to save a timestamped backup instead of crashing.
-   **"Module not found"**: Double-click `setup.bat` to repair the environment.
-   **Test Mode**: If the script runs too fast and minimal data appears, check if `WOM_TEST_MODE=True` in `.env`.

---

## 🔒 Security Note
This project uses a `.env` file to store secrets. **NEVER** share your `.env` file or commit it to GitHub.
