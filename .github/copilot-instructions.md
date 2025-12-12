# Copilot Instructions for WOMDiscord Project

## Project Overview
This tool generates advanced RuneScape clan activity reports by correlating Wise Old Man (WOM) XP gains with Discord message activity. It uses a local SQLite database for data persistence and supports complex reporting periods (30-day, 150-day, custom ranges).

## Architecture
- **Orchestration**: `main.py` manages the entire workflow: syncing DB, fetching WOM data, and generating reports.
- **Database**: `database.py` manages a SQLite `clan_data.db` containing `discord_messages` (raw history) and `wom_records` (snapshots).
- **Discord Integration**: `bot.py` handles historical message fetching with robust backfilling and gap detection.
- **WOM Integration**: `wom.py` provides an async client for the Wise Old Man API with rate limiting and pagination.

## Key Workflows
1.  **Discord Sync**:
    *   **Backfill**: Detects gaps between the configured start date (Feb 14, 2025) and the earliest DB record.
    *   **Forward Sync**: Fetches new messages since the latest DB record.
    *   **Activity Tracking**: Logic parses "Bridge Bot" messages (`**Username**:`) and direct user messages.
2.  **WOM Data Fetching**:
    *   Triggers a group update via `update_group`.
    *   Fetches "Gains" for multiple periods: 30 days, 150 days, and Custom (Feb 14 - Dec 8).
    *   Fetches "Activity" logs (joins/leaves) for the last 30 days.
3.  **Reporting**:
    *   **Database Snapshot**: Saves the run's aggregated stats to `wom_records`.
    *   **Excel Export**: Generates a formatted Excel file (`clan_report_summary_merged.xlsx`) with:
        *   Conditional formatting (Red text for 0 activity).
        *   Summary tables (Top 3 XP, Top 3 Chatters, New Members, Left Members).
    *   **CSV Export**: Raw data dump.

## Data Schema & Conventions
- **Database**:
    *   `discord_messages`: Stores `id`, `author`, `content`, `created_at` (UTC). Indexed on `created_at`.
    *   `wom_records`: Stores snapshots of calculated stats (`xp_30d`, `msg_30d`, etc.) per user per run.
- **Dates**: STRICTLY use timezone-aware UTC datetimes for all comparisons and API calls.
- **Usernames**: Normalized to lowercase for cross-referencing between Discord and WOM.
- **Configuration**: Managed via `.env` (WOM_GROUP_ID, TOKENS, dates).

## Example Commands
- **Initialize/Update DB & Generate Report**: `python main.py`
- **Clean Rebuild**: Delete `clan_data.db` and run `python main.py` to trigger a full re-fetch.
- **Test Mode**: Set `TEST_MODE = True` in `main.py` to limit processing to the first 20 players.

## Integration Details
- **Bridge Bots**: The system specifically handles relay bots by parsing `**Username**:` from the message content to attribute the message to the correct RS player.
- **Rate Limits**: `wom.py` implements smart RPM tracking and automatic backoff for 429 errors.