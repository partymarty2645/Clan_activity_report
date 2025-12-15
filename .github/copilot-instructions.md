# Copilot Instructions for ClanStats Project

## 🧠 Project Context
This is a Python-based reporting tool for OSRS Clan Statistics. It fetches data from **Wise Old Man (WOM)** and **Discord** to generate comprehensive Excel reports.

## 🏗️ Core Architecture
*   **Entry Point**: `run_auto.bat` (calls `harvest.py` -> `report.py`).
*   **Data Ingestion (`harvest.py`)**:
    *   Uses `services/wom.py` and `services/discord.py`.
    *   Saves raw JSON snapshots (`raw_data`) to `wom_records` in `clan_data.db` (SQLite).
    *   MUST persist raw data to avoid re-fetching.
*   **Reporting (`report.py`)**:
    *   Reads `clan_data.db`.
    *   Uses `reporting/excel.py` for styling.
    *   Implements **Smart Baseline**: If a user joined after the "Period Start Date", use their Earliest Snapshot as the baseline. NEVER assume 0-gains just because old data is missing.

## 📝 Coding Standards

### 1. Data Integrity
*   **UTC Everywhere**: All timestamps must be timezone-aware UTC.
*   **Normalization**: Usernames are strictly `lowercase` in code/DB, but capitalized for display.
*   **Persistence**: Any new API fetch must store the full JSON response in the database.

### 2. Output Formatting
*   **Dates**: Output dates in **EU Format (`%d-%m-%Y`)**, e.g., `14-02-2025`.
*   **Excel**:
    *   Use `openpyxl` via `reporting/excel.py`.
    *   Columns must preserve the specific order: `Username`, `Joined date`, `Role`, `XP 7d`, `Msg 7d`, etc.
    *   Apply conditional formatting (Red text for 0).

### 3. File Handling
*   **Path Safety**: Use `os.path.join(os.getcwd(), ...)` or absolute paths.
*   **Concurrency**: Do not lock the database for long periods. Use short transactions.
*   **Logging**: Use the `app.log` rotator.

## ⛔ Anti-Patterns (Do Not Do)
*   **Do NOT** use `main.py` (Deprecated). Use `harvest.py` or `report.py`.
*   **Do NOT** suggest standard backfills for missing users. Use "Smart Baseline" logic instead.
*   **Do NOT** hardcode API keys. Use `core/config.py` loading from `.env`.