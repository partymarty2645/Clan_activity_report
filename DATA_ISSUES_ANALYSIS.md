# Data Issues Analysis

## Problems Identified ❌

### 1. **clan_members IDs Not Populated**
- Total: 404 members
- With ID: Only 101 (25%)
- With joined_at: 0 (0%)
- **Root Cause**: Phase 2.2 migrations were supposed to populate these, but they're missing
- **Impact**: FK relationships broken for 303 members (75%)

### 2. **Discord Message User IDs Not Populated**
- Total: 587,222 messages
- With user_id FK: Only 309,793 (52.8%)
- **Root Cause**: Only found matches for ~53% of messages (rest are bots/deleted users - expected)
- **Impact**: 277,429 messages (47.2%) can't be linked to clan members

### 3. **No Boss Kill Data in Dashboard**
- boss_snapshots table has data: 427,557 rows
- kills column exists and has data
- **Root Cause**: JSON export shows 0 boss kills because data export isn't including kills data
- **Impact**: Dashboard shows no performance metrics

### 4. **Stale Data in Database**
- 404 total members but user says actual clan is ~300
- **Root Cause**: Old members haven't been cleaned up or database is from old export
- **Impact**: Inflated numbers, stale records

---

## What Needs to Happen

### Immediate Fixes (Data Population)

1. **Populate clan_members IDs for 303 missing members**
   - Option A: Re-run migration with better matching
   - Option B: Manually update from WOM API response
   - Option C: Delete stale members, re-harvest fresh

2. **Add joined_at dates to all 404 members**
   - Should come from WOM API
   - Migration should populate from harvest data

3. **Ensure Discord messages link to members**
   - Currently 309K/587K linked (52.8%)
   - Rest are likely bots/system messages (acceptable)
   - Just needs verification

4. **Include boss kill data in JSON export**
   - boss_snapshots.kills data exists in database
   - export_sqlite.py needs to include in dashboard JSON

### Root Cause Fixes

**Issue 1: IDs not populated**
- Check if Phase 2.2 migration actually ran
- Run: `python -m alembic current` to see last migration
- Re-run migration if needed: `python -m alembic upgrade head`

**Issue 2: WOM data not in dashboard**
- export_sqlite.py needs to query boss data
- Current implementation may not be fetching from boss_snapshots table
- Need to: SELECT boss_name, kills FROM boss_snapshots WHERE wom_snapshot_id IN (...)

**Issue 3: 404 vs 300 members**
- Need to clean database or re-harvest fresh
- Run: `python main.py` with current clan data to update

---

## Recommendation

The system is **architecturally correct** but **data-wise stale/incomplete**:

1. Back up current database
2. Re-run `python main.py` to harvest fresh data from WOM + Discord APIs
3. This will:
   - Get latest 300 active members
   - Populate IDs correctly
   - Include boss kill data
   - Clean up stale records

Would you like me to:
- [ ] Check which migrations have been applied?
- [ ] Re-run data harvest with fresh API calls?
- [ ] Fix the JSON export to include boss data?
- [ ] All of the above?
