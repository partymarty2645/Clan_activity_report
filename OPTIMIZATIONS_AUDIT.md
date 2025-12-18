# Optimization Audit Report
**Date:** 2025-12-17
**Status:** Post-Backfill Audit

## 🛑 Critical Issues (Immediate Attention)

### 1. Memory Safety in `report.py` (Message Counting)
- **Problem**: `count_messages` fetches ALL messages in a date range into a Python list (`msgs = db.execute(stmt).scalars().all()`). With ~500k messages, this consumes significant RAM (hundreds of MBs).
- **Risk**: OOM crashes if history grows.
- **Fix**: 
  - Use **Server-Side Filtering**: If possible, use SQL `LIKE '%**%**:%'` to verify structure before fetching.
  - **Generator/Chunking**: Use `yield_per(1000)` or `limit/offset` to process messages in batches.

## ⚠️ Efficiency Improvements (High Impact)

### 2. Database Maintenance Strategy
- **Problem**: The database grows indefinitely. Deletes (like deduplication) leave "holes" (fragmentation) that are not reclaimed until `VACUUM`.
- **Recommendation**:
  - Integrate `VACUUM INTO` (via `optimize_db.py`) into a weekly or monthly maintenance schedule (e.g., via `main_maintenance.py`).
  - Do NOT run full vacuum daily.

### 3. Harvest "Deep Sync" Logic
- **Problem**: `process_wom_snapshots_deep` fetches *all* history for all members.
- **Improvement**: It currently checks existing timestamps (good), but fetching from API is still costly. Ensure `WOM_DEEP_SCAN` is only enabled when necessary (User instruction), not default.

## ⚡ Code & API Optimizations (Medium Impact)

### 4. `backfill_missing_history` (in `report.py`)
- **Problem**: Fetches entire history (`get_player_snapshots`) when a user misses a single data point.
- **Fix**: Use `start_date` parameter in `get_player_snapshots` to fetch only missing window closer to the target date.

### 5. Regex Compilation
- **Observation**: `regex = re.compile(...)` is inside the loop in `count_messages`? 
  - *Correction*: It is outside the loop (line 109). This is correct. ✅

### 6. WOM Cache Management `services/wom.py`
- **Problem**: `_cache` grows indefinitely within the session until TTL expires or process restarts.
- **Fix**: Implement a `max_size` (e.g., 1000 entries) to prevent potential leak in long-running processes (daemon mode).

## 🧹 Workspace Hygiene
- **Action Taken**: Deleted one-off scripts:
  - `backfill.py`
  - `restore.py`
  - `deduplicate.py`
  - `data_stats.py`
  - `run_backfill.bat`
  - `clan_data.db.bak` (Note: Backup file remains until you manually delete it for safety).

---

## Recommended Next Steps
1. **Implement Chunking** for `count_messages` in `report.py`.
2. **Schedule Maintenance**: Create a `maintenance.bat` that runs the safe optimization once a week.
