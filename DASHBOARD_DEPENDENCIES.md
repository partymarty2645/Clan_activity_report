# Dashboard Dependencies Audit

## Overview
The dashboard (`index.html` / `clan_dashboard.html`) loads data from multiple sources and expects specific data structures. This document maps all dependencies and identifies potential failure points.

---

## 1. Data Load Chain

### Primary Data Source
**File:** `clan_data.json` (or `clan_data.js`)  
**Location:** `docs/clan_data.json`  
**Load Method:** 
- First tries `window.dashboardData` (pre-loaded from `clan_data.js`)
- Falls back to fetch `clan_data.json`

**Status:** ✅ EXISTS (verified in docs/clan_data.json)

### Secondary Data Source  
**File:** `ai_data.js`  
**Location:** `docs/ai_data.js`  
**Expected Structure:**
```javascript
window.aiData = {
  insights: [...],
  generated_at: "...",
  pulse: [...]
}
```
**Status:** ⚠️ **UNKNOWN** - Script loads but may be missing or have incorrect structure

---

## 2. Required Data Fields in `clan_data.json`

### Core Collections (Arrays)
| Field | Type | Used In | Status |
|-------|------|---------|--------|
| `allMembers` | Array | All tabs | ✅ Present |
| `history` | Array | Activity Trend chart | ✅ Present |
| `activity_heatmap` | Array(24) | Messages → Heatmap | ✅ Present |
| `topXPYear` | Array | XP Gains tab | ✅ Present |
| `topXPGainers` | Array | General → 5 cards | ⚠️ Generated if missing |
| `topBossers` | Array | Bosses tab | ❓ Not verified |
| `topMessenger` | Object | News ticker | ❓ Not verified |
| `risingStar` | Object | News ticker | ❓ Not verified |

### Chart Data Objects
| Field | Type | Expected | Status |
|-------|------|----------|--------|
| `chart_boss_diversity` | Object | Boss diversity donut | ✅ Present |
| `chart_raids` | Object | Raids bar chart | ✅ Present |
| `chart_skills` | Object | Skill mastery chart | ✅ Present |
| `chart_boss_trend` | Object | Boss trend line | ✅ Present |
| `correlation_data` | Object | XP correlation | ❓ Not verified |
| `clan_records` | Object | Leaderboard data | ❓ Not verified |

### Metadata
| Field | Type | Status |
|-------|------|--------|
| `generated_at` | String (ISO) | ✅ Present |
| `config` | Object | ⚠️ Can be missing (uses defaults) |

---

## 3. Member Object Structure (for `allMembers`)

Expected fields per member:
```javascript
{
  // Identity
  username: String,
  role: String,
  rank_img: String,
  
  // Activity (7-day)
  xp_7d: Number,
  boss_7d: Number,
  msgs_7d: Number,
  
  // Activity (30-day)
  xp_30d: Number,
  boss_30d: Number,
  msgs_30d: Number,
  
  // Activity (annual/year)
  xp_year: Number,
  
  // Total lifetime
  total_xp: Number,
  total_boss: Number,
  msgs_total: Number,
  
  // Clan membership
  joined_at: String (Date),
  days_in_clan: Number,
  
  // Boss preferences
  favorite_boss: String,
  favorite_boss_img: String,
  favorite_boss_all_time: String,
  favorite_boss_all_time_img: String,
  
  // Rendering
  context_class: String
}
```

---

## 4. External Dependencies (CDN)

| Library | Purpose | CDN URL | Criticality |
|---------|---------|---------|-------------|
| Chart.js 4.4.0 | Data visualization | cdn.jsdelivr.net | **HIGH** |
| G2Plot | Advanced charts | unpkg.com/@antv | **HIGH** |
| FontAwesome 6.5.1 | Icons | cdnjs.cloudflare.com | **MEDIUM** |
| Vanilla Tilt | 3D effects | cdnjs.cloudflare.com | **LOW** |
| Poppers.js | Tooltips | unpkg.com/@popperjs | **LOW** |
| Tippy.js | Tooltips | unpkg.com/tippy.js | **LOW** |
| Particles.js | Background | cdn.jsdelivr.net | **MEDIUM** |
| SweetAlert2 | Modals | cdn.jsdelivr.net | **LOW** |
| CountUp.js | Animations | cdnjs.cloudflare.com | **LOW** |

**Risk:** If CDN is down, charts won't render.

---

## 5. Local Dependencies

### CSS Files
- `assets/styles.css` - Main styles
- `assets/dynamic_styles.css` - Generated styles

### JS Files
- `dashboard_logic.js` - All rendering logic
- `clan_data.js` - Pre-loaded data
- `ai_data.js` - AI insights

---

## 6. Known Failure Points

### 🔴 High Risk
1. **Missing `chart_` objects** → Charts render blank/white
   - Example: `chart_boss_diversity`, `chart_raids`, `chart_skills`, `chart_boss_trend`
   - Fix: Ensure export_sqlite.py populates these fields

2. **Empty or null `allMembers`** → Entire dashboard fails
   - Risk: Members not exported, data pipeline incomplete
   - Safeguard: Added `if (!Array.isArray(...))` checks

3. **Missing `ai_data.js`** → AI Insights tab blank, News ticker fails
   - Current: No graceful fallback in code

4. **Member object missing key fields** → Cards and tables show "undefined"
   - Example: Missing `xp_7d`, `boss_7d`, `msgs_7d`
   - Risk: Export script doesn't compute all fields

### ⚠️ Medium Risk
5. **`history` array empty/short** → Activity Trend chart fails to render
   - Cause: Only populated if historical data exists (30+ day window)
   - Current: Safeguard added, shows "No trend data"

6. **CDN unavailable** → All charts fail (Chart.js, G2Plot needed)
   - Risk: No offline fallback

7. **Stale cache** → Old data served from `clan_data.js`
   - Browser caching: `?v=12` query param helps, but not foolproof

### 🟡 Low Risk
8. **`ai_data.js` malformed JSON** → window.aiData undefined
   - Current: Code checks `window.aiData` existence, has fallback

---

## 7. Data Generation Checklist

✅ = Present  
⚠️ = Needs verification  
❌ = Missing or broken

### export_sqlite.py Must Populate:
- ✅ `generated_at`
- ✅ `activity_heatmap` (24 elements)
- ✅ `history` (daily records with date, xp, msgs)
- ✅ `allMembers` (all required fields per member)
- ✅ `topXPYear` (sorted by xp_year)
- ✅ `chart_boss_diversity` (labels + datasets)
- ✅ `chart_raids` (labels + datasets)
- ✅ `chart_skills` (labels + datasets)
- ✅ `chart_boss_trend` (boss_name + chart_data)
- ⚠️ `chart_correlation_data` (if used)
- ⚠️ `clan_records` (if used)
- ⚠️ `config` (optional, uses defaults)

### mcp_enrich.py Must Populate:
- ⚠️ `ai_data.js` with `window.aiData` global
- ⚠️ `insights` array (10-12 items minimum)
- ⚠️ `pulse` array (5+ tickers minimum)

---

## 8. Recommended Fixes

### Immediate (Critical)
1. **Add fallbacks for missing charts** in `renderAllCharts()`
   ```javascript
   if (!dashboardData.chart_boss_diversity) {
       console.warn("Missing chart_boss_diversity");
       document.getElementById('container-boss-diversity').innerHTML = 
           '<div>No boss diversity data</div>';
   }
   ```

2. **Verify ai_data.js exists** and has correct structure
   ```javascript
   if (!window.aiData || !window.aiData.insights) {
       window.aiData = { insights: [], pulse: [] };
   }
   ```

3. **Add console warnings** for missing fields
   ```javascript
   if (!member.xp_7d) console.warn("Member missing xp_7d:", member.username);
   ```

### Short-term
4. Add data validation layer that checks all required fields before rendering
5. Create a test file that validates `clan_data.json` schema
6. Add "Data Health" section to dashboard showing which fields are present/missing

### Long-term
7. Implement error boundary/fallback UI for completely missing data
8. Add offline mode with last-known-good data
9. Cache validation on load

---

## 9. Test Checklist

Before deployment, verify:
- [ ] `clan_data.json` loads successfully
- [ ] `clan_data.js` pre-loads successfully  
- [ ] `ai_data.js` loads successfully
- [ ] All 6 member fields render (xp_7d, boss_7d, msgs_7d, etc.)
- [ ] All 4 main charts render (boss diversity, raids, skills, trend)
- [ ] Activity heatmap renders (24 bars)
- [ ] All tabs show data, not blank pages
- [ ] News ticker shows at least 3 items
- [ ] AI Insights shows at least 5 cards
- [ ] No console errors related to "undefined" or "cannot read property"

