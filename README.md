# ClanStats: Advanced OSRS Clan Tracking

A robust, enterprise-grade tool for tracking Old School RuneScape (OSRS) clan statistics by correlating **Wise Old Man (WOM)** XP data with **Discord** activity.

## 🚀 Key Features

*   **Integrated Tracking**: Merges game progress (XP/Bosses) with social engagement (Discord messages).
*   **"Smart Baseline" Logic**: Correctly handles new members joining mid-period by using their first available snapshot as usage baseline (no more "zero data" errors).
*   **Discord Sync**: Tracks message counts, "questions asked", and "favorite words" via efficient local database caching.
*   **Name Change Detection**: Automatically detects and handles OSRS name changes.
*   **Raw Persistence**: Stores full raw JSON responses from APIs to build a comprehensive historical "Data Pool".
*   **Excel Reporting**: Generates a polished, conditionally formatted Excel report with:
    *   **Custom Columns**: `7d`, `30d`, `70d`, `150d`, and `Total` periods.
    *   **Joined Date**: Displayed in EU format (DD-MM-YYYY).
    *   **Auto-Styling**: Color-coded columns (Identity, XP, Messages, Bosses).

## 🛠️ Architecture

The project follows a modular pipeline design:

1.  **Harvest (`harvest.py`)**:
    *   The "Heavy Lifter". Fetches data from WOM and Discord.
    *   Saves everything to `clan_data.db`.
    *   *Resilient*: Can run while the Excel report is open without crashing.

2.  **Report (`report.py`)**:
    *   The "Analyst". Reads `clan_data.db`.
    *   Calculates gains, activity scores, and text analytics.
    *   Generates `clan_report_summary_merged.xlsx`.
2.  **Report (`report.py`)**:
    *   The "Analyst". Reads `clan_data.db`.
    *   Calculates gains, activity scores, and text analytics.
    *   Generates `clan_report_summary_merged.xlsx`.
    *   Syncs to Google Drive (if configured).

3.  **Orchestrator (`main.py`)**:
    *   The "Conductor". Sequentially runs Harvest followed by Report.
    *   Ensures a clean execution pipeline.

4.  **Configuration (`config.yaml`)**:
    *   **Dynamic Settings**: Edit colors, role points, and report settings without touching code.
    *   Values are loaded by `core/config.py`.

5.  **Migrations (`alembic`)**:
    *   Manages database schema changes safely and automatically.

## 📦 Installation & Setup

### Prerequisites
*   **Python 3.10+**: [Download](https://www.python.org/downloads/) (IMPORTANT: Check the box **"Add Python to PATH"** during installation).

### 1. Setup
1.  Unzip the project folder to your desired location (e.g. Desktop).
2.  Double-click `setup.bat`.
    *   This will verify Python is installed.
    *   It will create a virtual environment and install necessary libraries.
    *   It will generate a `config.yaml` and `.env` file if they don't exist.

### 2. Configuration (`.env`)
The first time you run `setup.bat`, it creates a `.env` file. Open this file with Notepad and fill in your keys:

| Key | Description | Required? |
| :--- | :--- | :--- |
| `WOM_API_KEY` | Wise Old Man API Key. | ✅ Yes |
| `WOM_GROUP_ID` | Your WOM Group ID (e.g. `11114`). | ✅ Yes |
| `WOM_GROUP_SECRET`| Verification Code (needed to trigger auto-updates). | ✅ Yes |
| `DISCORD_TOKEN` | Discord Bot Token (Requires "Message Content Intent" enabled). | ✅ Yes |
| `RELAY_CHANNEL_ID`| (Optional) Stats will be posted to this Discord Channel ID. | ❌ No |
| `LOCAL_DRIVE_PATH`| (Optional) Full path to a Google Drive folder to auto-copy reports to. | ❌ No |

### 3. Advanced Settings (Optional)
These settings are also in `.env` but can usually be left at default:

| Key | Description | Default |
| :--- | :--- | :--- |
| `CUSTOM_START_DATE` | Date to start calculating "Total" stats from. | `2025-02-14` |
| `WOM_TEST_MODE` | Set to `true` to only fetch 5 members (for debugging). | `false` |
| `DAYS_LOOKBACK` | How far back to scan Discord messages. | `30` |

### 4. Visual Customization (`config.yaml`)
You can customize the look of the report in `config.yaml`:
*   **Role Weights**: Change how many points each role gets for ranking.
*   **Colors**: Change the Hex codes for the Excel columns (Identity, XP, Messages, Bosses).
*   **Aesthetics**: Toggle "Excel Dark Mode".
*   **WOM Settings**: Adjust update speeds and delays.

## 🏃 Usage

### Generate Report
Double-click **`run_auto.bat`**. 
This script will:
1.  Trigger a group update on Wise Old Man.
2.  Fetch the latest snapshots and Discord messages.
3.  Calculate gains based on your configured periods (7d, 30d, etc).
4.  Generate `clan_report_summary_merged.xlsx`.
5.  (Optional) Copy the file to your Google Drive folder.


## 📊 Output Explaination

The final output is **`clan_report_summary_merged.xlsx`**.

| Column | Description |
| :--- | :--- |
| **Username** | OSRS Player Name. |
| **Joined date** | Date joined the group (DD-MM-YYYY). |
| **Role** | Clan Role (Owner, Deputy, Member, etc). |
| **XP Gained [Period]** | Total XP gained in 7d/30d/70d/150d. |
| **Messages [Period]** | Discord messages sent in 7d/30d/70d/150d. |
| **Boss Kills [Period]** | Boss KC gained in 7d/30d/70d/150d. |

**Formatting Rules:**
*   **Cornflower Blue**: Identity Info (Name, Date, Role).
*   **Green**: XP Gains.
*   **Orange**: Message Counts.
*   **Yellow**: Boss Kills.
*   **Red Text**: Indicates `0` activity/gains.
