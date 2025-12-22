# ClanStats Implementation Progress Tracker

**Status:** Phase 1 - Foundation (In Preparation)  
**Last Updated:** 2025-12-22  
**Estimated Completion:** 2026-01-30 (6 weeks)  
**Project Duration:** ~240 hours (1-2 developers)

---

## 📋 Quick Reference for AI Sessions

### When to Start a New Chat Session

**⚠️ START NEW CHAT SESSION WHEN:**

1. **Context Window Approaching 80%+** (every 50-70k tokens)
   - Use this file to rebuild context
   - Previous session file: Reference `[IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)` first
   - Format: "Starting session N, continuing from [Phase/Step]"

2. **Major Phase Completion**
   - After Phase 1 completion (Week 2)
   - After Phase 2 completion (Week 3)
   - After Phase 3 completion (Week 4+)

3. **Debugging Major Issues**
   - If stuck on a problem for >30 minutes without progress
   - Archive old session, document issue clearly in this file

4. **Switching Tasks**
   - Moving from implementation to testing
   - Moving from DB work to API work

### How to Rebuild Context in New Session

**Paste This:**
```
I'm continuing ClanStats implementation from this progress file: [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)

Current Status: [COPY STATUS SECTION]
Current Phase: [COPY CURRENT PHASE SECTION]
Next Steps: [COPY NEXT IMMEDIATE STEPS]

Files already created: [LIST FILES]
Files pending: [LIST FILES]
```

---

## 📊 Overall Implementation Status

```
PHASE 1: Foundation (Weeks 1-2)
├── Issue #3: Username Normalization         ⬜ NOT STARTED
├── Issue #4: Role Mapping Authority          ⬜ NOT STARTED
├── Issue #9: Configuration Management        ⬜ NOT STARTED (config.py exists, needs validation)
├── Issue #5: Test Infrastructure             ⬜ NOT STARTED
└── [Week 1-2 Target: 40 hours]

PHASE 2: Core Architecture (Weeks 2-3)
├── Issue #2: API Client Coupling & DI        ⬜ NOT STARTED
├── Issue #1: Database Schema Refactoring     ⬜ NOT STARTED
└── [Week 2-3 Target: 60 hours]

PHASE 3: Polish & Scale (Weeks 3-4)
├── Issue #7: Discord Timezone Bugs           ⬜ NOT STARTED
├── Issue #8: Performance Optimization        ⬜ NOT STARTED
├── Issue #11: Observability                  ⬜ NOT STARTED
└── [Week 3-4 Target: 50 hours]

FINAL: Testing & Deployment (Week 4+)
├── Integration Testing                       ⬜ NOT STARTED
├── Production Validation                     ⬜ NOT STARTED
└── [Week 4+ Target: 40 hours]
```

---

## 🎯 PHASE 1: Foundation (Weeks 1-2)

### Current Step
**Last Action:** Plan created, preparation phase.  
**Next Action:** Start Issue #3 (Username Normalization)

---

### Issue #3: Brittle Username Normalization

**Priority:** 🔴 START HERE  
**Complexity:** Medium  
**Effort:** 1 day (8 hours)  
**Files Affected:** 5  
**Tests Required:** Yes

#### Tasks

- [ ] **1.3.1 Create `core/usernames.py`**
  - File: `core/usernames.py`
  - Status: ⬜ NOT STARTED
  - Includes: `UsernameNormalizer` class with:
    - `normalize(name, for_comparison=True)`
    - `canonical(name)`
    - `are_same_user(name1, name2)`
  - Lines of Code: ~120
  - Notes: 
    - Handles spaces, underscores, hyphens, unicode
    - Validates for unusual characters
    - Returns empty string for None/invalid input

- [ ] **1.3.2 Update `core/utils.py` (Deprecation Wrapper)**
  - File: `core/utils.py`
  - Status: ⬜ NOT STARTED
  - Change: Add deprecation wrapper for `normalize_user_string()`
  - Impact: Backward compatible
  - Lines Modified: ~10
  - Notes: Still supports old function, warns on deprecation

- [ ] **1.3.3 Update `scripts/harvest_sqlite.py`**
  - File: `scripts/harvest_sqlite.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Import `UsernameNormalizer` from `core.usernames`
    - Replace `normalize_user_string()` calls with `UsernameNormalizer.normalize()`
    - Use `canonical()` for Discord message author names
  - Lines Modified: ~15
  - Validate: After changes, ensure harvest still runs without errors

- [ ] **1.3.4 Update `scripts/report_sqlite.py`**
  - File: `scripts/report_sqlite.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Remove `robust_norm()` function
    - Import and use `UsernameNormalizer.normalize()`
  - Lines Modified: ~10
  - Validate: Report generation should produce identical output

- [ ] **1.3.5 Create Tests for Usernames**
  - File: `tests/test_usernames.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Test Cases:
    - `test_normalize_spaces()` - J O H N → johndoe
    - `test_normalize_underscores_hyphens()` - Jo_hn-Doe
    - `test_normalize_unicode_spaces()` - Non-breaking space, zero-width space
    - `test_normalize_empty_string()` - Empty/None handling
    - `test_are_same_user()` - JO HN vs john comparison
    - `test_canonical()` - Display-safe format
  - Test Count: 6+ tests
  - Expected Result: All tests pass, 100% function coverage

#### Validation Checklist
- [ ] All tests in `tests/test_usernames.py` pass
- [ ] `pytest tests/test_usernames.py -v` shows no failures
- [ ] `core/utils.py` deprecation wrapper shows warning on old function use
- [ ] `scripts/harvest_sqlite.py` runs without errors
- [ ] `scripts/report_sqlite.py` generates report with no changes to output
- [ ] No import errors in any updated file
- [ ] No regressions in existing functionality

**Blockers:** None  
**Dependencies:** None  

---

### Issue #4: Scattered Role Mapping Authority

**Priority:** 🟠 MEDIUM  
**Complexity:** Low  
**Effort:** 1 day (6 hours)  
**Files Affected:** 3  
**Tests Required:** No (simple Enum)

#### Tasks

- [ ] **1.4.1 Create `core/roles.py`**
  - File: `core/roles.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Includes:
    - `ClanRole` Enum with 9 roles (OWNER, DEPUTY_OWNER, ZENYTE, DRAGONSTONE, SAVIOUR, ADMINISTRATOR, MEMBER, PROSPECTOR, GUEST)
    - Metadata: api_name, tier, permissions dict
    - `RoleAuthority` class with static methods:
      - `is_leadership(role)`
      - `is_officer(role)`
      - `can_manage(role)`
      - `can_kick(role)`
      - `get_tier(role)`
      - `from_api_name(name)` - safe conversion from API string
  - Lines of Code: ~80
  - Notes: Centralizes all role logic, permissions stored in metadata

- [ ] **1.4.2 Update `reporting/moderation.py`**
  - File: `reporting/moderation.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Remove hardcoded `TIER_1_ROLES` list
    - Import `ClanRole`, `RoleAuthority` from `core.roles`
    - Replace role checks with `RoleAuthority.is_leadership()`, etc.
  - Lines Modified: ~20
  - Validate: All role checks use centralized authority

- [ ] **1.4.3 Update `reporting/enforcer.py`**
  - File: `reporting/enforcer.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Update role references to use `RoleAuthority`
  - Lines Modified: ~10
  - Validate: Enforcer suite works with new role system

#### Validation Checklist
- [ ] `core/roles.py` imports without errors
- [ ] `ClanRole` enum has all 9 roles
- [ ] `RoleAuthority.is_leadership()` correctly identifies T1 roles
- [ ] `RoleAuthority.from_api_name('owner')` returns `ClanRole.OWNER`
- [ ] `reporting/moderation.py` uses centralized roles
- [ ] `reporting/enforcer.py` uses centralized roles
- [ ] No hardcoded role lists remain in codebase

**Blockers:** None  
**Dependencies:** None  

---

### Issue #9: Configuration Management Scattered

**Priority:** 🟠 MEDIUM  
**Complexity:** Medium  
**Effort:** 1 day (4 hours, mostly validation)  
**Files Affected:** 2  
**Tests Required:** Yes (validation tests)

#### Tasks

- [ ] **1.5.1 Validate `core/config.py` (Update if needed)**
  - File: `core/config.py`
  - Status: ⏳ EXISTS, NEEDS VALIDATION
  - Verify:
    - All env variables loaded correctly
    - YAML config loading works (if used)
    - Fallback defaults in place
    - Precedence: Env > YAML > Defaults
  - Key Configs to Verify:
    - `DB_FILE` - path to clan_data.db
    - `DISCORD_TOKEN`, `RELAY_CHANNEL_ID`
    - `WOM_API_KEY`, `WOM_GROUP_ID`, `WOM_GROUP_SECRET`
    - `LOCAL_DRIVE_PATH`
    - Rate limits, batch sizes, timeouts
  - Create: `ConfigValidator` class with `validate_config()` method
  - Lines Modified: ~50
  - Notes: Fail-fast pattern, clear error messages

- [ ] **1.5.2 Add Config Validation in `main.py`**
  - File: `main.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Add `Config.fail_fast()` at pipeline start
    - Log all loaded config values (with sensitive redaction)
    - Exit with clear error if validation fails
  - Lines Modified: ~15
  - Example Error:
    ```
    Configuration invalid:
    - WOM_API_KEY is missing or empty
    - DISCORD_TOKEN is missing or empty
    Please check your .env file
    ```
  - Validate: `main.py` can't run without valid config

#### Validation Checklist
- [ ] `Config.validate()` returns list of errors (empty if valid)
- [ ] `Config.fail_fast()` raises ValueError if config invalid
- [ ] All critical keys are checked: WOM_API_KEY, DISCORD_TOKEN, WOM_GROUP_ID
- [ ] Env variables override YAML config
- [ ] YAML config overrides defaults
- [ ] `main.py` calls `Config.fail_fast()` at startup
- [ ] Error message clearly indicates missing keys
- [ ] No config loaded until validation passes

**Blockers:** None  
**Dependencies:** None  
**Notes:** This issue is low-risk because config.py likely exists; we're just validating/enhancing

---

### Issue #5: Test Infrastructure Setup

**Priority:** 🔴 CRITICAL  
**Complexity:** Medium  
**Effort:** 1.5 days (12 hours)  
**Files Affected:** 4 (NEW)  
**Tests Required:** Yes

#### Tasks

- [ ] **1.6.1 Create `tests/conftest.py`**
  - File: `tests/conftest.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Includes:
    - pytest fixtures for async tests (event_loop)
    - Fixtures for mock_wom, mock_discord
    - Fixture to reset ServiceFactory after each test
    - pytest.ini configuration (if needed)
  - Lines of Code: ~50
  - Key Fixtures:
    - `event_loop` - creates new event loop per test
    - `mock_wom` - MockWOMClient instance
    - `mock_discord` - MockDiscordService instance
    - `reset_factory` - cleanup after each test (autouse=True)

- [ ] **1.6.2 Create `tests/mocks.py`**
  - File: `tests/mocks.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Includes:
    - `MockWOMClient` class with:
      - `requests` list (track all calls)
      - `responses` dict (preset responses)
      - `fail_on_next` attribute (trigger failures)
      - Methods: `get_group_members()`, `get_player_details()`, `update_player()`, `close()`
    - `MockDiscordService` class with:
      - `requests` list
      - `responses` dict
      - Methods: `fetch()`, `close()`
  - Lines of Code: ~80
  - Notes:
    - Mocks are simple, just return preset data
    - No real API calls
    - Can fail on demand (for error testing)

- [ ] **1.6.3 Create `tests/test_usernames.py`**
  - File: `tests/test_usernames.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Tests: See Issue #3 above (6+ tests)
  - Lines of Code: ~100

- [ ] **1.6.4 Create `tests/__init__.py`**
  - File: `tests/__init__.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Content: Empty or minimal (makes tests a package)
  - Lines: ~2

#### Dependencies for Test Infrastructure
- pytest (already in requirements.txt)
- pytest-asyncio (needs to be added to requirements.txt)
- aioresponses (optional, for mocking aiohttp - may add later)

#### Validation Checklist
- [ ] `pytest --collect-only` shows all test files discovered
- [ ] `pytest tests/test_usernames.py -v` passes
- [ ] `pytest tests/ --co` lists all tests
- [ ] Fixtures in conftest.py are accessible to all tests
- [ ] `mock_wom` fixture returns MockWOMClient instance
- [ ] `mock_discord` fixture returns MockDiscordService instance
- [ ] ServiceFactory reset after each test
- [ ] No test pollution (tests don't affect each other)

**Blockers:** None  
**Dependencies:** pytest-asyncio (add to requirements.txt)  

---

### Phase 1 Completion Checklist

**Overall Status:** ⬜ NOT STARTED

- [ ] All Issue #3 tasks complete and validated
- [ ] All Issue #4 tasks complete and validated
- [ ] All Issue #9 tasks complete and validated
- [ ] All Issue #5 tasks complete and validated
- [ ] No regression in existing functionality
- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] `main.py` validates config at startup
- [ ] All deprecated functions log warnings
- [ ] Code review completed
- [ ] Changes committed to git

**Week 1-2 Deliverables:**
- ✅ `core/usernames.py` - Single source of truth for normalization
- ✅ `core/roles.py` - Centralized role authority
- ✅ `core/config.py` - Enhanced with validation
- ✅ `tests/conftest.py`, `tests/mocks.py` - Test infrastructure
- ✅ `tests/test_usernames.py` - First test suite
- ✅ Updated scripts using new modules
- ✅ All changes backward compatible

---

## 🔧 PHASE 2: Core Architecture (Weeks 2-3)

### Status
**Overall:** ⬜ NOT STARTED  
**Est. Start Date:** 2026-01-06  
**Est. End Date:** 2026-01-20

---

### Issue #2: API Client Coupling & Dependency Injection

**Priority:** 🔴 HIGH  
**Complexity:** High  
**Effort:** 2 days (16 hours)  
**Files Affected:** 4  
**Tests Required:** Yes

#### Tasks

- [ ] **2.1.1 Create `services/factory.py`**
  - File: `services/factory.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Includes:
    - `ServiceFactory` class with:
      - `get_wom_client()` - lazy singleton with thread safety
      - `get_discord_service()` - lazy singleton with thread safety
      - `set_wom_client(client)` - for test injection
      - `set_discord_service(service)` - for test injection
      - `cleanup()` - graceful shutdown
      - `reset()` - reset for testing
  - Lines of Code: ~100
  - Notes:
    - Thread-safe using asyncio.Lock
    - Lazy initialization (created only when first accessed)
    - Allows dependency injection for testing

- [ ] **2.1.2 Update `services/wom.py` (Thread Safety)**
  - File: `services/wom.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Add `_session_lock` asyncio.Lock
    - Update `_get_session()` with lock
    - Add `_validate_response()` method for response validation
    - Add response caching validation
  - Lines Modified: ~30
  - Notes:
    - Prevents session creation race conditions
    - Validates API responses before caching

- [ ] **2.1.3 Update `scripts/harvest_sqlite.py` (Accept Injection)**
  - File: `scripts/harvest_sqlite.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Modify `run_sqlite_harvest()` to accept optional wom_client, discord_service args
    - Use factory if not injected
    - Remove global singleton imports at top level
  - Lines Modified: ~20
  - Validate: Can pass mock clients to harvest for testing

- [ ] **2.1.4 Update `main.py` (Use Factory)**
  - File: `main.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Import `ServiceFactory` instead of direct clients
    - Add `await ServiceFactory.cleanup()` in finally block
    - Log client initialization
  - Lines Modified: ~10
  - Validate: Pipeline works with factory pattern

- [ ] **2.1.5 Create `tests/test_harvest.py` (E2E Test)**
  - File: `tests/test_harvest.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Tests:
    - `test_harvest_with_mock_wom()` - Full harvest with mock
    - `test_harvest_handles_api_failure()` - Error handling
    - `test_discord_messages_stored()` - Discord data persistence
  - Lines of Code: ~150
  - Notes: Tests use MockWOMClient and MockDiscordService from conftest

#### Validation Checklist
- [ ] `ServiceFactory.get_wom_client()` returns WOMClient instance
- [ ] Mocking works: `ServiceFactory.set_wom_client(mock)` uses mock
- [ ] Thread-safe: Multiple concurrent calls don't create multiple instances
- [ ] `harvest_sqlite.py` can accept injected clients
- [ ] `test_harvest.py` passes with mocked APIs
- [ ] `ServiceFactory.cleanup()` closes all connections
- [ ] No global singleton state remains

**Blockers:** Phase 1 must be complete  
**Dependencies:** Test infrastructure from Phase 1

---

### Issue #1: Database Schema Refactoring

**Priority:** 🔴 HIGH  
**Complexity:** Very High  
**Effort:** 3 days (24 hours)  
**Files Affected:** 8+  
**Tests Required:** Yes (critical)
**⚠️ RISK LEVEL:** HIGH - Database migration

#### Pre-Migration Checklist
- [ ] Full database backup created: `backups/clan_data_YYYYMMDD_HHMMSS.db`
- [ ] Test backup restored successfully
- [ ] Alembic configured and working
- [ ] All team members notified
- [ ] Rollback plan documented
- [ ] Data validation tests written

#### Tasks

- [ ] **2.2.1 Create Migration: Drop Unused Tables**
  - File: `alembic/versions/drop_unused_tables.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Changes:
    - `upgrade()`: DROP TABLE skill_snapshots, activity_snapshots
    - `downgrade()`: Recreate tables for rollback
  - Lines: ~40
  - Safety: Test on backup first

- [ ] **2.2.2 Create Migration: Add User IDs**
  - File: `alembic/versions/normalize_user_ids.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Changes:
    - Add `clan_members.id` (Integer, Auto-increment)
    - Populate IDs from ROWID
    - Make id primary key
    - Add `wom_snapshots.user_id` (FK)
    - Add `discord_messages.user_id` (FK)
    - Drop `wom_snapshots.username`
  - Lines: ~80
  - Safety: High risk, test thoroughly

- [ ] **2.2.3 Create Migration: Add Indexes**
  - File: `alembic/versions/add_missing_indexes.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Indexes:
    - `(user_id, timestamp)` on wom_snapshots
    - `(snapshot_id)` on boss_snapshots
    - `(created_at)` on discord_messages
    - `(author_name, created_at)` on discord_messages
  - Lines: ~50
  - Safety: Read-only, low risk

- [ ] **2.2.4 Update `database/models.py`**
  - File: `database/models.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Update `ClanMember` model: id as PK
    - Update `WOMSnapshot`: add user_id FK
    - Update `BossSnapshot`: add snapshot_id FK constraint
    - Update `DiscordMessage`: add user_id FK
    - Remove unused model classes (SkillSnapshot, ActivitySnapshot)
  - Lines Modified: ~50
  - Validate: SQLAlchemy can create tables from models

- [ ] **2.2.5 Create `utils/migration_helper.py`**
  - File: `utils/migration_helper.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Helper Functions:
    - `backup_database()` - safe backup before migration
    - `verify_migration()` - run integrity checks
    - `rollback_migration()` - restore from backup
  - Lines: ~100

- [ ] **2.2.6 Create `tests/test_database_integrity.py`**
  - File: `tests/test_database_integrity.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Tests:
    - `test_no_orphaned_boss_snapshots()`
    - `test_no_orphaned_discord_messages()`
    - `test_no_orphaned_wom_snapshots()`
    - `test_all_users_have_snapshots()`
  - Lines: ~150
  - Notes: Run after each migration

- [ ] **2.2.7 Update Queries to Use IDs**
  - File: `core/analytics.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Replace username-based queries with user_id queries
    - Use `.where(WOMSnapshot.user_id == user_id)` instead of `.where(WOMSnapshot.username == name)`
    - Use joinedload for performance
  - Lines Modified: ~100
  - Performance Impact: 100x faster queries

- [ ] **2.2.8 Run Migrations on Staging**
  - Manual Step
  - Status: ⬜ NOT STARTED
  - Process:
    1. Copy production DB to staging
    2. Run migration 001: drop unused tables
    3. Run migration 002: add user IDs
    4. Run migration 003: add indexes
    5. Run integrity tests
    6. Verify no data loss
    7. If OK, run on production backup
    8. If OK, run on production (with downtime)

#### Validation Checklist
- [ ] Backup created before any migration
- [ ] `alembic current` shows latest migration applied
- [ ] No orphaned records detected by integrity tests
- [ ] Query performance improved (100x faster)
- [ ] All analytics queries use new ID-based approach
- [ ] No references to username in foreign keys remain
- [ ] `pytest tests/test_database_integrity.py -v` passes
- [ ] Rollback tested successfully
- [ ] Data counts match before/after migration

**Blockers:** API decoupling (Issue #2) should be done first  
**Dependencies:** Phase 1 complete, test infrastructure ready  
**⚠️ CRITICAL:** Database backup required before any migration

---

### Phase 2 Completion Checklist

**Overall Status:** ⬜ NOT STARTED

- [ ] All Issue #2 (API DI) tasks complete and validated
- [ ] All Issue #1 (DB Schema) tasks complete and validated
- [ ] Database integrity tests all pass
- [ ] No performance regression
- [ ] Rollback tested and works
- [ ] All new tests pass: `pytest tests/test_harvest.py tests/test_database_integrity.py -v`
- [ ] Code review completed
- [ ] Changes committed to git with detailed messages

**Week 2-3 Deliverables:**
- ✅ `services/factory.py` - Dependency injection for API clients
- ✅ `tests/test_harvest.py` - E2E harvest testing
- ✅ Three database migrations (drop unused, add IDs, add indexes)
- ✅ `tests/test_database_integrity.py` - Data validation
- ✅ Updated `core/analytics.py` - ID-based queries
- ✅ `utils/migration_helper.py` - Safe migration utilities

---

## 🚀 PHASE 3: Polish & Scale (Weeks 3-4)

### Status
**Overall:** ⬜ NOT STARTED  
**Est. Start Date:** 2026-01-20  
**Est. End Date:** 2026-02-03

---

### Issue #7: Discord Timezone Bugs

**Priority:** 🟠 MEDIUM  
**Complexity:** Low  
**Effort:** 1 day (6 hours)  
**Files Affected:** 3  
**Tests Required:** Yes

#### Tasks

- [ ] **3.1.1 Create `core/timestamps.py`**
  - File: `core/timestamps.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Includes:
    - `TimestampHelper` class with static methods:
      - `now_utc()` - current UTC time
      - `to_utc(dt)` - convert any datetime to UTC
      - `cutoff_days_ago(days)` - UTC cutoff
      - `validate_timestamp(ts)` - verify timestamp is reasonable
      - `format_for_display(dt)` - format for user display
  - Lines: ~80
  - Notes: All internal logic uses UTC, conversion only at display

- [ ] **3.1.2 Update `scripts/harvest_sqlite.py`**
  - File: `scripts/harvest_sqlite.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Import `TimestampHelper` from `core.timestamps`
    - When storing Discord messages: use `TimestampHelper.to_utc(msg.created_at)`
    - When fetching WOM data: ensure timestamps are UTC
  - Lines Modified: ~10

- [ ] **3.1.3 Update `core/analytics.py`**
  - File: `core/analytics.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Replace hardcoded datetime calculations with `TimestampHelper.cutoff_days_ago()`
    - All filtering uses UTC cutoffs
  - Lines Modified: ~15

#### Validation Checklist
- [ ] All timestamps in database are UTC
- [ ] `TimestampHelper.to_utc()` handles naive datetimes (assumes UTC)
- [ ] Cutoff calculations use UTC
- [ ] Stored Discord message timestamps match API (timezone-converted to UTC)
- [ ] Analytics queries filter by UTC cutoffs
- [ ] Display formatting preserves original intent

**Blockers:** None  
**Dependencies:** Phase 2 (because of database changes)

---

### Issue #8: Performance Optimization at Scale

**Priority:** 🟠 MEDIUM  
**Complexity:** Medium  
**Effort:** 2 days (16 hours)  
**Files Affected:** 2  
**Tests Required:** Yes (performance benchmarks)

#### Tasks

- [ ] **3.2.1 Add Bulk Query Methods to `core/analytics.py`**
  - File: `core/analytics.py`
  - Status: ⬜ NOT STARTED
  - Methods:
    - `get_user_snapshots_bulk(session, user_ids)` - fetch latest for multiple users
    - `get_discord_message_counts_bulk(session, author_names, cutoff)` - single query
  - Lines Added: ~60
  - Notes:
    - Use SQLAlchemy `joinedload()` to avoid N+1 queries
    - Use compound queries instead of loops

- [ ] **3.2.2 Profile Report Generation**
  - Manual Step
  - Status: ⬜ NOT STARTED
  - Process:
    1. Run `python -m cProfile -s cumulative scripts/report_sqlite.py > profile.txt`
    2. Identify slowest functions
    3. Optimize top 3-5 bottlenecks
    4. Re-profile to verify improvement
  - Target: Reduce from 5-10s to <2s

- [ ] **3.2.3 Create Performance Benchmark**
  - File: `tests/test_performance.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Benchmarks:
    - Report generation time <2s (1000+ members)
    - Dashboard export time <1s
    - Analytics query time <100ms
  - Lines: ~80

#### Validation Checklist
- [ ] Profiling shows <2s report generation
- [ ] Bulk queries execute in single DB queries
- [ ] No N+1 query patterns remain
- [ ] Performance benchmarks pass
- [ ] No memory leaks (check peak memory usage)

**Blockers:** Database refactoring (Phase 2)  
**Dependencies:** Phase 2

---

### Issue #11: Missing Observability

**Priority:** 🟡 LOW  
**Complexity:** Medium  
**Effort:** 2 days (12 hours)  
**Files Affected:** 3  
**Tests Required:** Yes

#### Tasks

- [ ] **3.3.1 Create `core/observability.py`**
  - File: `core/observability.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Includes:
    - Trace ID context management
    - `get_trace_id()` - get or generate
    - `set_trace_id(id)` - set for context
    - `TraceIDFilter` - logging filter
    - `setup_observability()` - configure logging
  - Lines: ~100
  - Notes: Trace IDs help correlate events across distributed logs

- [ ] **3.3.2 Update `main.py` (Add Checkpoints)**
  - File: `main.py`
  - Status: ⬜ NOT STARTED
  - Changes:
    - Call `setup_observability()` at startup
    - Log checkpoints before/after each step:
      - "PIPELINE_START"
      - "CHECKPOINT: Config Validation"
      - "CHECKPOINT: Harvest Start/End"
      - "CHECKPOINT: Report Start/End"
      - "PIPELINE_SUCCESS" or "PIPELINE_FAILURE"
  - Lines Modified: ~20
  - Trace Example:
    ```
    2026-01-20 14:23:00 [INFO] [abc12def] Orchestrator: PIPELINE_START
    2026-01-20 14:23:05 [INFO] [abc12def] Orchestrator: CHECKPOINT: Harvest Complete
    2026-01-20 14:24:15 [INFO] [abc12def] Orchestrator: PIPELINE_SUCCESS
    ```

- [ ] **3.3.3 Create `tests/test_observability.py`**
  - File: `tests/test_observability.py` (NEW)
  - Status: ⬜ NOT STARTED
  - Tests:
    - `test_trace_id_generation()` - generates if not set
    - `test_trace_id_context()` - persists across calls
    - `test_logging_includes_trace_id()` - logs contain trace ID
  - Lines: ~60

#### Validation Checklist
- [ ] Trace IDs appear in all logs
- [ ] Trace ID remains same for entire pipeline run
- [ ] Log format: `[TIMESTAMP] [LEVEL] [TRACE_ID] [MODULE] MESSAGE`
- [ ] `app.log` shows all checkpoints
- [ ] No performance impact from observability

**Blockers:** None  
**Dependencies:** Phase 2

---

### Phase 3 Completion Checklist

**Overall Status:** ⬜ NOT STARTED

- [ ] All Issue #7 (Timezone) tasks complete
- [ ] All Issue #8 (Performance) tasks complete
- [ ] All Issue #11 (Observability) tasks complete
- [ ] Performance benchmarks pass: <2s report, <1s export
- [ ] All tests pass: `pytest tests/ -v --tb=short`
- [ ] Code review completed
- [ ] Changes committed to git

**Week 3-4 Deliverables:**
- ✅ `core/timestamps.py` - UTC-centric timestamp handling
- ✅ `core/observability.py` - Structured logging with trace IDs
- ✅ `tests/test_performance.py` - Performance benchmarks
- ✅ `tests/test_observability.py` - Observability tests
- ✅ Updated analytics with bulk queries
- ✅ Main pipeline enhanced with checkpoints

---

## 📝 PHASE 4: Integration & Testing (Week 4+)

### Status
**Overall:** ⬜ NOT STARTED  
**Est. Start Date:** 2026-02-03  
**Est. End Date:** 2026-02-10

---

### Integration Testing

- [ ] **4.1 Full Pipeline Test**
  - Manual Step
  - Process:
    1. Start fresh with backup DB
    2. Run `python main.py`
    3. Verify all 4-5 steps complete
    4. Check output files generated
    5. Verify dashboard created

- [ ] **4.2 Regression Testing**
  - Manual Step
  - Process:
    1. Run full test suite: `pytest tests/ -v`
    2. Code coverage check: `pytest --cov=core,services,scripts tests/`
    3. All tests pass with >80% coverage

- [ ] **4.3 Load Testing**
  - Manual Step
  - Process:
    1. Create test database with 1000+ members
    2. Run harvest: verify performance
    3. Run report generation: measure time
    4. Verify memory usage stays reasonable

### Production Validation

- [ ] **4.4 Staging Deployment**
  - Manual Step
  - Process:
    1. Deploy to staging server
    2. Run with real API keys (staging group)
    3. Monitor for 24 hours
    4. Verify data accuracy
    5. Check performance under real load

- [ ] **4.5 Production Rollout**
  - Manual Step with Backup Plan
  - Process:
    1. Schedule maintenance window
    2. Create production backup
    3. Deploy new code
    4. Run `python main.py` once
    5. Verify dashboard and reports
    6. Monitor for issues
    7. Have rollback plan ready

---

## 🎯 Implementation Decisions Log

### Decision 1: Phased Approach
**Date:** 2025-12-22  
**Decision:** Implement in 3 phases (Foundation → Architecture → Polish)  
**Rationale:** Each phase is buildable on its own; reduces risk of massive simultaneous changes  
**Status:** ✅ APPROVED

### Decision 2: Test-First Infrastructure
**Date:** 2025-12-22  
**Decision:** Set up mocks and test infrastructure (conftest.py) in Phase 1  
**Rationale:** Enables safe testing of Phase 2 database migrations without hitting real APIs  
**Status:** ✅ APPROVED

### Decision 3: Database Migration Strategy
**Date:** 2025-12-22  
**Decision:** Use Alembic migrations with backup + rollback plan  
**Rationale:** Safe, traceable, reversible schema changes; industry standard  
**Status:** ✅ APPROVED

### Decision 4: Subprocess Isolation
**Date:** 2025-12-22  
**Decision:** Keep existing subprocess model in main.py (don't change to direct imports)  
**Rationale:** Stability; each script runs in clean environment; matches GEMINI.md conventions  
**Status:** ✅ APPROVED

---

## 📌 Known Risks & Mitigation

### Risk 1: Database Migration Data Loss

**Severity:** 🔴 CRITICAL  
**Likelihood:** Low (with proper testing)  
**Impact:** Complete data loss if migration fails  

**Mitigation:**
- Backup database before each migration
- Test migrations on backup first
- Run integrity tests after each step
- Have rollback scripts ready
- Notify users of maintenance window

### Risk 2: API Changes During Implementation

**Severity:** 🟠 MEDIUM  
**Likelihood:** Low (WOM/Discord APIs stable)  
**Impact:** Harvest or parsing could break  

**Mitigation:**
- Keep mock services simple and flexible
- Monitor API status pages
- Have fallback error handling
- Document API version assumptions

### Risk 3: Context Window Overflow

**Severity:** 🟡 LOW  
**Likelihood:** High (will happen every 2-3 days)  
**Impact:** Loss of progress if session not properly closed  

**Mitigation:**
- This file as permanent memory
- New chat sessions every 50-70k tokens
- Clear handoff format for context restore
- Archive completed phases

### Risk 4: Configuration Drift

**Severity:** 🟠 MEDIUM  
**Likelihood:** Medium (multiple env files)  
**Impact:** Hard-to-debug issues from wrong settings  

**Mitigation:**
- Centralized config.py with validation
- Fail-fast at startup
- Log all config values (redacted)
- Document all config options

---

## 🔄 Session Handoff Template

**Use this template when starting a new session:**

```
I'm continuing ClanStats implementation.

## Context Restoration

Reference File: [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)

**Current Phase:** [Phase 1/2/3/4]
**Current Step:** [Step number and name]
**Session Number:** [N]

## What's Complete
[Copy from "Overall Status" section - list completed items]

## What's In Progress
[Copy current task]

## What's Next
[Copy next 2-3 tasks]

## Files Already Created
[List files]

## Files Pending
[List files to create]

## Build Context
Please search for:
1. `core/usernames.py` - If it exists, we're past Phase 1
2. `services/factory.py` - If it exists, we're in Phase 2+
3. `tests/conftest.py` - Test infrastructure status

## Important Notes
[Any blockers, decisions, or gotchas from previous session]
```

---

## 📊 Success Metrics (Target State)

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Test Coverage | 0% | 80%+ | ⬜ |
| Config Files (scattered) | 15+ | 1 centralized | ⬜ |
| Username Normalization (duplicates) | 3 copies | 1 function | ⬜ |
| Role Mapping (scattered) | 3+ files | 1 source | ⬜ |
| Report Generation Time | 5-10s | <2s | ⬜ |
| Query Performance | 100-200ms | <50ms | ⬜ |
| Code Duplication (overall) | High | Low | ⬜ |
| Automated Testing | None | Full CI/CD ready | ⬜ |
| API Client Coupling | High (global singletons) | Low (DI) | ⬜ |
| Database Integrity | Manual checks | Automatic validation | ⬜ |
| Observability | Minimal | Full trace IDs + checkpoints | ⬜ |
| Maintainability Index | ~5/10 | 8/10 | ⬜ |

---

## 📞 Support & Escalation

### If You Get Stuck

1. **Check this file first** - Search for the issue in "Known Risks"
2. **Review validation checklist** - For current step
3. **Check existing code** - Similar patterns may exist elsewhere
4. **Search workspace** - Use semantic_search tool to find related code
5. **Document in this file** - Add to "Issues Encountered" section below

### Issues Encountered

*[This section tracks problems found during implementation]*

- None yet (pre-implementation)

---

## 📅 Timeline & Milestones

```
Week 1 (Jan 6-12):   Phase 1 - Foundation
├─ Mon-Tue: Username Normalization + Role Mapping
├─ Wed-Thu: Config Validation + Test Infrastructure
└─ Fri:     Integration & Review

Week 2 (Jan 13-19):  Phase 2 Start - API Decoupling
├─ Mon-Tue: ServiceFactory + Mock Tests
└─ Wed+:    Database Migration (careful!)

Week 3 (Jan 20-26):  Phase 2 Complete + Phase 3 Start
├─ Mon:     Database Migration Cleanup
├─ Tue-Wed: Timezone Handling
└─ Thu-Fri: Performance Optimization

Week 4+ (Jan 27+):   Phase 3 + Integration
├─ Testing & Validation
├─ Performance Benchmarks
└─ Production Rollout

Final: Feb 10, 2026
```

---

## ✅ Approval & Sign-Off

- [ ] Plan reviewed and approved by team lead
- [ ] All resources allocated
- [ ] Communication sent to stakeholders
- [ ] Backup procedures in place
- [ ] Rollback plan documented

---

**Last Updated:** 2025-12-22  
**Next Review:** After Phase 1 completion  
**Maintainer:** AI Implementation Agent  
**Version:** 1.0
