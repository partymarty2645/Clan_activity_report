# ClanStats: Database & Structural Audit Report

**Audit Conducted by:** Antigravity (Senior PhD Database Specialist)  
**Date:** 2025-12-30  
**Scope:** `database/`, `data/`, `scripts/`, `core/analytics.py`

---

## 1. Executive Summary

The ClanStats architecture is a robust "Process Isolation" model that successfully separates data ingestion from analysis. The use of SQLite with WAL mode and compound indexing shows strong maturity. However, the system is currently in a "Transitional State" (Phase 2.2.2), leading to architectural "split personalities" between username-based and ID-based logic.

---

## 2. Schema & Architectural Integrity

### 2.1 The "Duplicate Key" Anti-Pattern

The `boss_snapshots` table contains both `wom_snapshot_id` and `snapshot_id`.
> [!WARNING]
> While documented as "backward compatibility," this introduces risk of data divergence. If one is updated without the other, joins will fail silently.

### 2.2 Weak Referential Integrity

The SQLAlchemy models (`database/models.py`) define relationships via `Integer` columns rather than formal `ForeignKey` objects.

- **Risk**: SQLite does not enforce constraints unless explicitly enabled via `PRAGMA foreign_keys = ON`, and SQLAlchemy won't generate proper migrations for `ON DELETE CASCADE` without `ForeignKey` definitions.
- **Impact**: Deleting a `WOMSnapshot` might leave orphaned rows in `boss_snapshots`, leading to inflated aggregations.

### 2.3 Transition Debt (Phase 2.2.2)

There is significant code duplication between "legacy" username methods and "modern" ID methods in `core/analytics.py`.

- **Recommendation**: Formalize the transition. Legacy methods should be deprecated and redirected to ID-based methods via a helper to centralize the "Identity Resolution" logic.

---

## 3. Performance & Optimization

### 3.1 The JSON-in-Query Bottleneck

`AnalyticsService.get_skill_mastery` parses `raw_data` (JSON) from the database at runtime.
> [!CAUTION]
> On a database with millions of snapshots, this query will degrade linearly. JSON parsing in SQLite is functional but slow for aggregate statistics.

- **Recommendation**: De-normalize level data into a `skill_snapshots` table or a specialized `levels` JSONB-style column during the harvest phase.

### 3.2 Dynamic SQL `IN ({})` Construction

`Queries.py` frequently uses string formatting to build `IN` clauses (e.g., `snapshot_id IN ({})`).

- **Issues**:
    1. **SQL Limits**: SQLite has a `SQLITE_MAX_VARIABLE_NUMBER` (usually 999 or 32766). If `snapshot_ids` exceeds this, the query crashes.
    2. **Plan Caching**: Dynamic SQL forces the query planner to re-evaluate the plan for every variation of the list length.
- **Recommendation**: For large ID sets, use temporary tables or subqueries joining against a "selection" table.

### 3.3 Redundant Timestamp Logic

Timestamp parsing (handling ISO, 'Z', '+00:00') is re-implemented in `scripts/harvest_sqlite.py` and `core/analytics.py`.

- **Habit**: This should be strictly delegated to `core/timestamps.py` to ensure "One Source of Truth" for time.

---

## 4. Data Quality & "Bad Habits"

### 4.1 `INSERT OR REPLACE` Side Effects

`UPSERT_MEMBER` uses `INSERT OR REPLACE`.

- **DANGER**: In SQLite, `REPLACE` is actually `DELETE` then `INSERT`. This triggers `ON DELETE` cascades (if FKs are enabled) and changes the internal `rowid`.
- **PHD Tip**: Use `INSERT INTO ... ON CONFLICT(username) DO UPDATE` (available in SQLite 3.24+). It preserves the primary key and avoids redundant index churn.

### 4.2 Silent Exception Swallowing

In `harvest_sqlite.py:492`, "UNIQUE constraint failed" is swallowed silently.

- **Risk**: While intended to handle re-runs, it masks cases where a snapshot might have been corrupted or overwritten with incomplete data.

### 4.3 Hardcoded Configuration

`scripts/harvest_sqlite.py` contains hardcoded paths for `DB_PATH` and `STATE_FILE`.

- **Hygiene**: These should be moved to `core/config.py` alongside other environment variables.

---

## 5. Top 10 Recommendations for Improvement

Based on the audit findings, here are the 10 most critical actions to take, ordered by impact vs. effort:

### 1. Enforce Strict Foreign Keys (Integrity)

**Action**: Update `database/models.py` to use `ForeignKey('table.id', ondelete='CASCADE')` for all relationships (`boss_snapshots`, `wom_snapshots`, `discord_messages`).
**Why**: Prevents orphaned records (e.g., ghost boss kills) when a snapshot or user is deleted. Essential for long-term data reliability.

### 2. Implement "ON CONFLICT DO UPDATE" (Stability)

**Action**: Replace `INSERT OR REPLACE` in `UPSERT_MEMBER` with `INSERT INTO ... ON CONFLICT(username) DO UPDATE`.
**Why**: `REPLACE` changes the `rowid` and can thrash indexes unnecessarily. `DO UPDATE` is atomic and preserves the row's identity and creation timestamp logic.

### 3. Unify Identity Resolution (Architecture)

**Action**: Create a `ResolverService` that handles `Username <-> ID` mapping centrally. Update `analytics.py` to use this service, deleting duplicate `_by_id` and legacy methods.
**Why**: Removes the "Split Personality" of the codebase. All queries should use IDs internally, with usernames only used at the edges (API I/O or Display).

### 4. Normalize Skill Data (Performance)

**Action**: Stop storing `raw_data` JSON for every snapshot if you only need 99s. Create a `skill_milestones` table or similar.
**Why**: JSON parsing at runtime for millions of rows is a scalability killer. Querying a specialized table for "Level 99s" is O(1) vs O(N) parsing.

### 5. Parameterize `IN` Clauses (Security/Stability)

**Action**: Refactor `Queries.py` to accept lists of parameters instead of formatting strings `IN ({})`. Use `executemany` or temporary tables for bulk operations.
**Why**: Prevents SQL injection risks (low here, but bad habit) and crashes when list > 999 items.

### 6. Centralize Config & Paths (Hygiene)

**Action**: Move `DB_PATH`, `STATE_FILE`, and other loose constants from `harvest_sqlite.py` and `optimize_database.py` into `core/config.py`.
**Why**: Single source of truth for configuration makes deployment and testing (mocking paths) significantly easier.

### 7. Deduplicate Timestamp Logic (Maintenance)

**Action**: Audit all files for `datetime.fromisoformat` and replace with `TimestampHelper.parse()`.
**Why**: Timezones are hard to get right. Having 5 different ways to parse dates ensures at least one of them will break during Daylight Savings or leap years.

### 8. Fix `boss_snapshots` Schema (Tech Debt)

**Action**: Drop the `wom_snapshot_id` column and rename `snapshot_id` to `wom_snapshot_id` (or standardize on `snapshot_id` everywhere).
**Why**: Having two columns for the same key is confusing and dangerous. Pick one name and stick to it.

### 9. Optimize Harvest State (Efficiency)

**Action**: The `harvest_state.json` file is a flat file. Move this state tracking into a `harvest_log` table in SQLite.
**Why**: Keeps transactional state with the data. process A cannot lock the file while process B reads it for reporting.

### 10. Add Data Integrity Tests (Quality)

**Action**: Add a specific test suite `tests/test_integrity.py` that verifies:

- No orphaned boss snapshots exist.
- Sum of boss kills matches `wom_snapshots.total_boss_kills`.
- No users have `NULL` joined_at dates.
**Why**: Catch logical drifts before they pollute your reports.
