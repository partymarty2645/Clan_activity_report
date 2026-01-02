# Dashboard Reliability Roadmap

**TL;DR:** Fix the data pipeline first (prevents garbage data), then unblock JS rendering bugs (enables charts to populate), then correct formulas (ensures accurate display). Three phases, ~135 minutes total, 95% issue resolution with minimal risk.

---

## Phase 1: Data Layer (30 min | Low Risk)

### 1.1 Fix `core/analytics.py` `get_trending_boss()` scaling bug
- **Issue**: `total_gain` displays as 4.3 instead of 130k+ (magnitude error)
- **Root Cause**: Likely division/scaling applied incorrectly when calculating kill count deltas
- **Why First**: Prevents bad data from corrupting all downstream consumers; single backend fix resolves one data source for multiple charts
- **Effort**: ~5 lines of code audit + 1-2 line fix
- **File**: [core/analytics.py](core/analytics.py)
- **Expected Outcome**: Boss trend chart displays correct magnitudes

### 1.2 Validate export_sqlite.py data serialization
- **Issue**: Ensure numbers aren't truncated/scaled during export
- **Quick Check**: Verify large values (1M+) pass through correctly
- **Effort**: Code review + 1-2 test validations
- **File**: [scripts/export_sqlite.py](scripts/export_sqlite.py)

---

## Phase 2: Critical JS Bugs (45 min | Low Risk)

### 2.1 Remove duplicate `renderXPContribution()` definition
- **Issue**: Two definitions in [docs/dashboard_logic.js](docs/dashboard_logic.js); second overwrites first
- **Line**: ~1866 (second definition)
- **Also Fix**: `ReferenceError: el is not defined` at line 1872 → change `el` to `container`
- **Effort**: Delete 50 lines, fix 1 variable name
- **Impact**: Unblocks chart rendering; prevents crashes

### 2.2 Add defensive null guards to 3 chart functions
**Files & Line Ranges:**
- `renderTenureChart()`: Add guard before bucket calculations
- `renderActivityTrend()`: Check if history array exists + has length > 0
- `renderLeaderboardChart()`: Guard before score calculation

**Guard Pattern:**
```javascript
if (!data || !Array.isArray(data) || data.length === 0) {
    container.innerHTML = '<div style="...">No data available</div>';
    return;
}
```

**Effort**: 3 functions × 2-3 guard lines each
**Impact**: Unblocks empty chart rendering; prevents silent failures

### 2.3 Apply fixes to BOTH HTML files
- **Why**: User requirement: edits to `clan_dashboard.html` must also sync to `docs/index.html`
- **Method**: Update `dashboard_logic.js` sections in both files identically
- **Validation**: Diff both files after edits to ensure synchronization
- **Files**: 
  - [clan_dashboard.html](clan_dashboard.html)
  - [docs/index.html](docs/index.html)

---

## Phase 3: Formula & Logic Issues (60 min | Medium Risk)

### 3.1 Reweight Leaderboard Composite Score formula
- **Current**: `(msgs_7d*20) + (xp_7d/5000) + (boss_7d*5)`
- **Problem**: XP dominates by 1000x due to magnitude (millions vs single digits)
- **Recommended Fix**: `(msgs*100) + (xp/100000) + (boss)` OR `(msgs*50) + (xp/50000) + (boss*2)`
  - Option A: Balanced all three metrics equally
  - Option B: XP slight priority
- **Location**: [docs/dashboard_logic.js](docs/dashboard_logic.js) `renderLeaderboardChart()` function
- **Effort**: Change 1 line; test with sample data
- **Validation**: Verify high-XP and high-message players rank appropriately
- **Impact**: Data accuracy; corrects leaderboard weighting

### 3.2 Fix Rising Star time period hardcoding
- **Issue**: Always uses `msgs_7d` regardless of user's period selection
- **Current Code**: `value: formatNumber(rising.msgs_7d)`
- **Fix**: Use dynamic `msgKey` variable like other stat cards
- **Location**: [docs/dashboard_logic.js](docs/dashboard_logic.js) `renderGeneralStats()` function (~line 430)
- **Change**: Replace `msgs_7d` with `msgKey` variable
- **Effort**: Change 1 variable name
- **Impact**: Respects user's 7d/30d period toggle

### 3.3 Define missing `--neon-purple` CSS variable
- **Issue**: `--neon-purple: #bc13fe` used in default boss theme but not defined
- **Location**: [assets/styles.css](assets/styles.css) in `:root` selector
- **Add**: `--neon-purple: #bc13fe;` to the CSS variables block
- **Effort**: 1 line CSS
- **Impact**: Ensures default theme color consistency; prevents browser fallback

---

## Phase 4: Architecture Refactor (Optional | 90 min | Medium Risk)

### 4.1 Consolidate BOSS_THEMES into CSS variables
- **Current**: Hardcoded BOSS_THEMES object in JS (~60 entries, 6 color categories)
- **Goal**: Move to CSS `:root` variables for single source of truth
- **Example**:
  ```css
  --boss-cyan: #00f3ff;
  --boss-cyan-glow: rgba(0, 243, 255, 0.4);
  --boss-purple: #aa00ff;
  --boss-purple-glow: rgba(170, 0, 255, 0.4);
  /* ... etc for all 6 categories */
  ```
- **Files**: 
  - [assets/styles.css](assets/styles.css) (add variables)
  - [docs/dashboard_logic.js](docs/dashboard_logic.js) (reference CSS vars)
  - [clan_dashboard.html](clan_dashboard.html) (sync changes)
  - [docs/index.html](docs/index.html) (sync changes)
- **Effort**: 40 lines CSS + 20 lines JS refactoring
- **Impact**: Prevents future styling bugs; improves team velocity

### 4.2 Remove hardcoded `themes` object from `renderGeneralStats()`
- **Current**: Local `themes` object duplicates BOSS_THEMES colors
- **Fix**: Reference global BOSS_THEMES or new CSS variables
- **Lines**: ~350-360 in [docs/dashboard_logic.js](docs/dashboard_logic.js)
- **Effort**: Delete 5 lines, update 1-2 references
- **Impact**: Single source of truth for colors

### 4.3 Create validation script
- **Purpose**: Prevent accidental divergence between `clan_dashboard.html` and `docs/index.html`
- **Method**: Simple hash/diff check before commits
- **Example Script**:
  ```bash
  #!/bin/bash
  # Compare dashboard_logic.js sections in both HTML files
  diff <(grep -A 5000 "dashboard_logic.js" clan_dashboard.html) \
       <(grep -A 5000 "dashboard_logic.js" docs/index.html)
  ```
- **Integration**: Run in CI/pre-commit hook
- **Effort**: ~20 lines script

---

## Sequencing Rationale

| Phase | Why This Order | Risk | Effort | Impact |
|-------|---|---|---|---|
| **1 (Data)** | Garbage-in/garbage-out principle. Fix data source before rendering logic. Prevents cascading errors. | Low | 30 min | Unblocks all downstream consumers |
| **2 (JS)** | Rendering crashes block all testing. Fix critical JS errors before tweaking formulas. | Low | 45 min | All charts render without errors |
| **3 (Logic)** | Formula corrections safer when foundation is stable. Lower risk of cascading failures. | Medium | 60 min | Data displays accurately |
| **4 (Refactor)** | Optional but improves long-term maintainability. Do last to avoid integration issues. | Medium | 90 min | Prevents future bugs |

---

## Expected Outcome After Phase 1–3

✅ All charts render (no crashes)
✅ Data displays at correct magnitude (4.3 → 130k fix)
✅ Formulas weight activity correctly (balanced scoring)
✅ Time period selection respected (7d/30d toggle works)
✅ Both HTML files synchronized
✅ **~135 minutes of work; ~95% of issues resolved**

---

## Validation Checklist

- [ ] Phase 1: `get_trending_boss()` fixed; test with real data
- [ ] Phase 2: No duplicate functions; null guards in place; both HTML files identical
- [ ] Phase 3: Leaderboard scores balanced; Rising Star respects period toggle; CSS variables defined
- [ ] Phase 4 (Optional): BOSS_THEMES consolidated; no hardcoded color duplication
- [ ] All charts render without errors (browser console clean)
- [ ] Dashboard loads successfully on page refresh
- [ ] Git status clean; ready for commit

---

## Files to Modify

**Core**:
- [core/analytics.py](core/analytics.py) — Fix trending boss calculation
- [assets/styles.css](assets/styles.css) — Add --neon-purple CSS variable

**Frontend**:
- [docs/dashboard_logic.js](docs/dashboard_logic.js) — Fix JS bugs, formulas, guards
- [clan_dashboard.html](clan_dashboard.html) — Sync changes from docs/dashboard_logic.js
- [docs/index.html](docs/index.html) — Sync changes from docs/dashboard_logic.js
- [scripts/export_sqlite.py](scripts/export_sqlite.py) — Validate data serialization (Phase 1.2)

---

## Implementation Status

- [x] Phase 1: Data Layer (30 min) — COMPLETE ✅
- [x] Phase 2: Critical JS Bugs (45 min) — COMPLETE ✅
- [x] Phase 3: Formula & Logic Issues (60 min) — COMPLETE ✅
- [ ] Phase 4: Architecture Refactor (90 min - Optional)
- [ ] Final Validation & Commit

---

**Started**: January 2, 2026
**Phases 1-3 Completed**: January 2, 2026
**Actual Time**: ~20 minutes
**Target Phase 4**: Optional consolidation of BOSS_THEMES into CSS variables
