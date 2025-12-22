# ClanStats: Advanced OSRS Clan Tracking

A robust, enterprise-grade tool for tracking Old School RuneScape (OSRS) clan statistics by correlating **Wise Old Man (WOM)** XP data with **Discord** activity.

## 🚀 Key Features

* **Integrated Tracking**: Merges game progress (XP/Bosses) with social engagement (Discord messages).
* **Discord Sync**: Tracks message counts, "questions asked", and "favorite words" via efficient local database caching.
* **Visual Dashboard**: A deployed HTML/JS Dashboard (via Google Drive) featuring:
  * **Activity Heatmaps**
  * **Performance Analytics**: Scatter plots ("Chatterbox vs Grinder"), Trend lines, and Skill Mastery clouds.
  * **Boss Highlight Grids**
  * **Purging Candidates**: Auto-lists inactive members (>30d tenure, 0 messages/XP).
  * **Live Search & Filtering**
* **Excel Reporting**: Generates a polished, conditionally formatted Excel report with:
  * **Custom Columns**: `7d`, `30d`, `Total` periods.
  * **Auto-Styling**: Color-coded columns (Identity, XP, Messages, Bosses).

## 🛠️ Architecture

The project follows a modular **Process Isolation** design (no shared memory state):

1. **Harvest (`scripts/harvest_sqlite.py`)**:
    * Fetches data from WOM API and Discord API.
    * Writes incrementally to `clan_data.db`.
    * Runs as an isolated subprocess.

2. **Report (`scripts/report_sqlite.py`)**:
    * Generates the classic `clan_report_summary_merged.xlsx` (Excel).
    * Syncs Excel files to Google Drive.

3. **Export (`scripts/export_sqlite.py`)**:
    * **The Dashboard Engine**.
    * Generates `clan_data.json` (Raw Data) and `clan_data.js` (Frontend Loader).
    * Deploys the static HTML Dashboard (`clan_dashboard.html` + `assets`) to the `docs/` folder (GitHub Pages ready).

4. **Orchestrator (`main.py`)**:
    * The "Conductor". Sequentially runs Harvest -> Report -> Export.
    * Ensures clean exits and error handling.

## 📦 Installation & Setup

### Prerequisites

* **Python 3.10+**: [Download](https://www.python.org/downloads/) (IMPORTANT: Check the box **"Add Python to PATH"** during installation).

### 1. Setup

1. Unzip the project folder.
2. Double-click `setup.bat`.
    * It creates a virtual environment and installs dependencies.
    * It generates a `.env` file for your keys.

### 2. Configuration (`.env`)

Fill in your keys in the `.env` file:

| Key | Description |
| :--- | :--- |
| `WOM_API_KEY` | Wise Old Man API Key. |
| `WOM_GROUP_ID` | Your WOM Group ID (e.g. `11114`). |
| `DISCORD_TOKEN` | Discord Bot Token (Requires "Message Content Intent"). |
| `LOCAL_DRIVE_PATH`| **Crucial**: Path to a Google Drive folder. The Dashboard will be deployed here! |

## 🏃 Usage

### Generate Report & Dashboard

Double-click **`run_auto.bat`**.
This script will:

1. Update database (WOM + Discord).
2. Generate Excel Reports.
3. **Deploy the Visual Dashboard** to your Google Drive folder.

### 3. Quick Actions (Slash Commands)

If using an AI Agent (like me), you can run these workflows directly:

| Command | Action |
| :--- | :--- |
| `/run-pipeline` | Runs the full **Harvest -> Report -> Export** cycle. The "Big Red Button". |
| `/verify-system` | Runs a full health check (JSON integrity, Drive audit, Data consistency). |
| `/generate-dashboard` | Re-generates the HTML/JSON only (skips fetching new data). Useful for design tweaks. |
| `/optimizedatabase` | Runs `PRAGMA` optimizations on the SQLite DB. |

## 📊 Outputs

### 1. Excel Report (`clan_report_summary_merged.xlsx`)

* The classic spreadsheet with conditional formatting (Green/Yellow/Red).
* Tracks XP, Messages, Boss Kills over 7d/30d/All-Time.

### 2. Visual Dashboard (`clan_dashboard.html`)

* **Live Web View**: Open `clan_dashboard.html` from your Google Drive folder.
* **Features**:
  * **Top Messenger / Top XP** Cards.
  * **Performance Analytics**:
    * **Activity Matrix**: Scatter plot identifying playstyles.
    * **Boss Trends**: Monthly trend lines for top kills.
    * **Diversity & Mastery**: Donut and bar charts for broad activity tracking.
  * **Boss Highlights Grid**: 3x3 grid of top boss killers with background art.
  * **Activity Heatmap**: When are your clan members sending messages?
  * **Full Roster**: Sortable table with Rank Icons.
