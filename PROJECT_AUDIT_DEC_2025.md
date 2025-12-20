# Clan Activity Project Audit - December 2025

**Status:** Critical Integration Review
**Auditor:** Antigravity Agent
**Date:** 19 Dec 2025

## 1. Executive Summary

The project is currently in a state of "Integration Drift". While the individual components (Database, Excel Generator, Web Dashboard) feature advanced logic, they are currently disconnected or misconfigured, leading to a broken user experience.

**Critical findings:**

1. **Excel:** The user flow is the opposite of what is desired (dashboard first vs data first).
2. **Web Dashboard:** Effectively non-functional due to data loading methods and potential asset path mismatches.
3. **Database:** A major schema shift (from `members` table to `wom_snapshots`) has likely orphaned older scripts or queries that haven't been fully updated.

---

## 2. Component Analysis

### A. The Excel Report (`reporting/excel.py`)

**Current State:**

- **Entry Point:** Opens a "Launch Dashboard" cover sheet with neon styling.
- **Structure:** Split between Dashboard and Roster, with incomplete metrics.

**New Requirements (User Defined):**

1. **Single View:** The Excel sheet must open directly to a single "Master Table" containing all players. No cover sheet.
2. **Column Structure (Strict Order):**
    1. Player Name
    2. Date Joined
    3. Rank (Stretch goal: Include Icon)
    4. Messages (Last Week)
    5. Messages (Last Month)
    6. Messages (Last 3 Months)
    7. XP (Last Week)
    8. XP (Last Month)
    9. XP (Last 3 Months)
    10. Boss KC (Last Week)
    11. Boss KC (Last Month)
    12. Boss KC (Last 3 Months)
    13. Yearly Messages
    14. Yearly XP
    15. Yearly Boss KC
3. **Styling:** Maintain the "Dark Mode / Neon" aesthetic. Zero values must be visually distinct (muted/red).

**Technical Gap:**

- Current `AnalyticsService` does not calculate "3 Months" (90d) or "Yearly" (365d) deltas explicitly for all metrics.
- Rank Icons in Excel are complex; we will attempt to insert images or use emoji/unicode backups if image insertion proves too heavy for performance.

### B. The Web Dashboard (`clan_dashboard.html`)

**Current State:**

- **Visuals:** High-end "Neon Gielinor" aesthetic (Glassmorphism, Hex codes).
- **Data Source:** Hybrid approach. It tries to load `clan_data.js` via `<script>` tag AND accepts injection.
- **Navigation:** Custom JS `switchSection`.

**Issues:**

1. **"No Data Loaded":**
    - The script `dashboard_export.py` writes to `clan_data.json` and patches `dashboard.html`, but `clan_dashboard.html` expects `window.dashboardData` to be present at boot.
    - If `clan_data.js` is missing or corrupt, the dashboard renders empty skeletons.
2. **"Images not found":**
    - The code references `assets/boss_${name}.png`.
    - *Audit Finding:* The `assets` folder contains `skill_*.png`. The existence of `boss_*.png` files is unverified or they are named incorrectly. A single typo breaks the image.
3. **"Navigation Broken":**
    - Likely caused by a JavaScript error halting execution before the event listeners for the navbar are attached. If the data load fails, the rest of the script crashes.

**Required Fixes:**

- [ ] **Unify Data Loading:** Force `dashboard_export.py` to write a valid `clan_data.js` file and rely solely on that.
- [ ] **Asset Audit:** creating a script to verify every boss name in the database has a corresponding `.png` and fallback to a default icon if missing.
- [ ] **Error Handling:** Wrap the startup logic in `try-catch` blocks so navigation works even if data is partial.

### C. The Database (`clan_data.db`)

**Current State:**

- **Schema:** The system looks for `wom_snapshots`, `wom_records`, etc.
- **Health:** A quick check revealed `sqlite3.OperationalError: no such table: members`.
- **Implication:** If any legacy code (or the user's manual queries) tries to access `members`, it will fail. The system has migrated to a Snapshot-based architecture (TimeSeries), which is better effectively but requires all tools to be updated.

**Required Fixes:**

- [ ] Ensure `dashboard_export.py` is fully decoupled from the old `members` table (It seems to be using `AnalyticsService`, which is good).
- [ ] Verify `AnalyticsService` effectively handles empty dates to prevent zero-division errors which crash the dashboard.

---

## 3. High-Level Recommendation Checklist

To get this project to the state you want ("Clean Excel" + "Functional Dashboard"), we need to perform these specific actions:

### Phase 1: Excel Simplification

1. **Refactor `core/analytics.py`:** Add explicit methods for `get_snapshots_at_cutoff` for 90 days and 365 days.
2. **Refactor `reporting/excel.py`:**
    - Delete the Dashboard cover sheet.
    - Implement the **15-column schema** defined above.
    - Apply conditional formatting (Green scales for gains, Muted for 0).
3. **Rank Icons:** Investigate inserting small images into the 'Rank' column or a dedicated adjacent column.

### Phase 2: Dashboard Resurrection

1. **Fix `clan_data.js`:** Ensure `dashboard_export.py` writes this file correctly.
2. **Debug Mode:** Add `console.log` traces to `clan_dashboard.html` to see exactly where it stops rendering.
3. **Asset Renaming:** Rename boss images to match the *exact* string keys from the database (e.g., `phantom_muspah` vs `muspah`).

### Phase 3: Data Verification

1. Run a full harvest to populate the `wom_snapshots`.
2. Verify the "Monthly" logic is actually fetching historical data points (this is the hardest part; if we don't have snapshots from February, we can't show February gains. We might need to improvise with 'Average' logic or mock data until real data accumulates).

## 4. Conclusion

The project "bones" are good, but the "skin" (UI/Excel) does not match the "muscles" (Database). We need to strip back the fancy Excel dashboard as requested and focus purely on getting the data piped correctly to the Web Dashboard.
