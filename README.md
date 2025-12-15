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
    *   Syncs to Google Drive (if configured).

3.  **Run (`run_auto.bat`)**:
    *   The entry point. Orchestrates Harvest -> Report automatically.

## 📦 Installation & Setup

### Prerequisites
*   **Python 3.10+**: [Download](https://www.python.org/) (Ensure "Add to PATH" is checked).
*   **Git**: [Download](https://git-scm.com/).

### 1. Installation
```bash
git clone https://github.com/partymarty2645/clanstats.git
cd clanstats
setup.bat
```

### 2. Configuration keys (`.env`)
Create a `.env` file in the root directory with the following keys:

| Key | Description | Required? |
| :--- | :--- | :--- |
| `WOM_API_KEY` | Wise Old Man API Key for group management. | ✅ Yes |
| `WOM_GROUP_ID` | The ID of your WOM Group (e.g., `11114`). | ✅ Yes |
| `DISCORD_TOKEN` | Bot token to fetch specific channel history. | ✅ Yes |
| `RELAY_CHANNEL_ID`| Channel ID to post summary (optional). | ❌ No |
| `GUILD_ID` | Discord Server ID (optional). | ❌ No |
| `LOCAL_DRIVE_PATH`| Path to sync Excel file (e.g., `G:\My Drive\...`). | ❌ No |

**(Note: This project does not require a Discord Bot to be *running* 24/7, but it needs a valid Token to fetch history via API.)**

## 🏃 Usage

### Standard Run
Double-click **`run_auto.bat`**.
This will:
1.  Fetch latest data (Harvest).
2.  Generate the Excel report.
3.  Back up previous files.
4.  Sync to Google Drive (if configured).

### Manual Run
```bash
# Fetch Data Only
python harvest.py

# Generate Report Only
python report.py
```

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
| **Questions (30d)** | Number of questions asked in chat. |
| **Favorite Word** | Most commonly used non-stopword. |

**Formatting Rules:**
*   **Cornflower Blue**: Identity Info (Name, Date, Role).
*   **Green**: XP Gains.
*   **Orange**: Message Counts.
*   **Yellow**: Boss Kills.
*   **Red Text**: Indicates `0` activity/gains.
