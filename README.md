# WomDiscordMVP: Clan Statistics & Tracking

A robust Python tool for tracking Old School RuneScape (OSRS) clan statistics by integrating **Wise Old Man (WOM)** API data with **Discord** message history.

## 🚀 Overview

This project automates the collection of clan member performance and engagement metrics. It bridges the gap between in-game gains (via WOM) and social activity (via Discord) to provide a comprehensive report for clan leaders.

## ✨ Key Features

-   **Discord Integration**: Scrapes and stores message counts for clan members from a specified Discord channel/server.
-   **Wise Old Man Sync**: Fetches player snapshots (XP, EHP, EHB, Boss Kills) directly from WOM.
-   **Hybrid Reporting**: Generates Excel (`.xlsx`) and CSV reports combining social and game stats.
-   **Ranking System**: auto-calculates "Rank Scores" based on member roles (e.g., Owner, admin, Member).
-   **Smart Name Matching**: Handles differences between Discord usernames and OSRS display names (e.g., `Luke_Jon` vs `Luke Jon`).
-   **Name Change Detection**: Automatically detects when a member changes their name on WOM and updates the local database to preserve history.
-   **Gap Filling**: Automatically backfills missing Discord message history if the database is incomplete.
-   **Resilience**:
    -   Handles API rate limits with exponential backoff.
    -   Safe file saving (prevents crashes if Reports are open in Excel).
    -   Automatic database backups.

## 🛠️ Prerequisites

-   **Python 3.10+**
-   **Git**
-   A **Discord User Token** (Self-bot) *OR* Bot Token (depending on setup, strictly uses user token logic currently).
-   A **Wise Old Man API Key**.

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/partymarty2645/clanstats.git
    cd clanstats
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

Create a `.env` file in the root directory. You can use the template below:

```ini
# --- Discord Configuration ---
# Your generic Discord User Token (Use with caution, self-botting rules apply)
DISCORD_TOKEN=your_discord_token_here

# ID of the server/guild to scrape
DISCORD_GUILD_ID=123456789012345678

# ID of the specific channel to scrape (optional, depending on bot logic)
DISCORD_CHANNEL_ID=123456789012345678

# --- Wise Old Man Configuration ---
# API Key from Wise Old Man Group Settings
WOM_API_KEY=your_wom_api_key_here

# The Group ID to track
WOM_GROUP_ID=12345

# The Secret Code for updating the group (Group Settings)
WOM_GROUP_SECRET=your_group_verification_code

# --- Report Settings ---
# Custom date range for "Total" columns
CUSTOM_START_DATE=2025-02-14
CUSTOM_END_DATE=2025-12-08

# Excel Styling
EXCEL_ZERO_HIGHLIGHT=true
EXCEL_ZERO_BG_COLOR=#FFC7CE
EXCEL_ZERO_FONT_COLOR=#9C0006

# --- Advanced / Tuning ---
WOM_RATE_LIMIT_DELAY=0.67
WOM_TARGET_RPM=90
WOM_MAX_CONCURRENT=5
WOM_TEST_MODE=False
```

## 🏃 Usage

Run the main script:

```bash
python main.py
```

### What happens next?
1.  **Backup**: Creates a backup of `clan_data.db`.
2.  **Archive**: Moves old CSV/Excel reports to `archive/`.
3.  **WOM Update**: Triggers a "Update All" on WOM to refresh member data.
4.  **Name Checks**: Scans for any member name changes since the last run.
5.  **Sync**:
    -   Fetches new Discord messages.
    -   Fetches fresh WOM snapshots for all members.
6.  **Report**: Generates:
    -   `clan_report_summary_merged.xlsx` (Formatted Excel)
    -   `clan_report_summary_merged.csv` (Raw Data)

## 📂 Project Structure

-   `main.py`: Entry point and orchestrator. Handles reporting and logic flow.
-   `database.py`: SQLite database interface. Handles message and snapshot storage.
-   `bot.py`: Discord fetching logic.
-   `wom.py`: Async client for Wise Old Man API.
-   `clan_data.db`: SQLite database (stores all history).

## ⚠️ Important Notes

-   **Discord ToS**: Using a user token to scrape messages ("self-botting") is technically against Discord ToS. Use at your own risk.
-   **Database**: The `clan_data.db` grows over time. Keep the `backups/` folder safe.

## 🤝 Contributing

1.  Fork the repo
2.  Create your feature branch (`git checkout -b feature/amazing-feature`)
3.  Commit your changes (`git commit -m 'Add some amazing feature'`)
4.  Push to the branch (`git push origin feature/amazing-feature`)
5.  Open a Pull Request
