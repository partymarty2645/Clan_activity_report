ClanStats Technical Implementation Plan
Based on Audit by: Codebase Audit Tool (2025-12-22) Strategy: "Safety First" - Foundations > Tests > Refactor > Optimizations.

Phase 1: Foundation (Cleanup & Standardization)
Goal: Eliminate "scattered truth" (configs, usernames, roles) before building heavy logic on top of it.

1.1 Centralize Configuration
Problem: Paths and settings are hardcoded in main.py, setup.bat, 
services/wom.py
.
Solution: Create 
core/config.py
.
Use pydantic-settings (if available) or strong typing for config.
Fail fast if .env is missing critical keys.
Define all paths (DB, Excel, Drive) in one place.
1.2 Username Normalization (Crucial!)
Problem: johndoe vs JohnDoe vs john_doe. Three different regexes currently exist.
Solution: Create core/usernames.py.
UsernameNormalizer.normalize(str) -> str: For database storage (strict).
UsernameNormalizer.display(str) -> str: For UI (preserves casing).
1.3 Role Authority
Problem: Check for "Officer" is repeated in 3 files with different lists.
Solution: Create core/roles.py.
Define ClanRole Enum.
Central list OFFICER_ROLES = [...].
Phase 2: Core Architecture (Safety & Structure)
Strategic Note: Unlike the audit which lists Database first, we will do API Decoupling & Config FIRST. Why? Because we need Tests to verify the Database migration, and we can't write Tests without Mock APIs.

2.1 API Decoupling & Dependency Injection
Problem: wom_client is a global singleton. Tests hit real API = Flaky & Slow.
Solution:
Create services/factory.py.
ServiceFactory.get_wom_client() returns either Real or Mock based on env.
Update harvest_sqlite.py to accept injected clients.
2.2 Test Infrastructure
Problem: 0% Coverage.
Solution:
Install pytest, pytest-asyncio.
Write tests/conftest.py using ServiceFactory to inject mocks.
Write one end-to-end test for "Harvest -> DB Store".
2.3 Database Refactor (The Big One)
Problem: String PKs are slow. Orphaned data risks.
Solution:
Backup: 
scripts/backup_db.py
 BEFORE running.
Cleanup: Drop unused tables (skill_snapshots, etc).
Migration:
Add clan_members.id (Integer, Auto-increment).
Add wom_snapshots.user_id (FK to members).
Add boss_snapshots.snapshot_id (FK to snapshots).
Indices: Add (user_id, timestamp) composite index for instant lookups.
2.4 Excel Reliability
Problem: Writing directly to final file causes corruption on crash.
Solution:
Write to clan_report_TEMP.xlsx.
On success, os.replace() to clan_report_summary_merged.xlsx (Atomic).
Phase 3: Polish & Scale
Goal: Make it fast and debuggable.

3.1 Timezone Hygiene
Problem: Discord harvest assumes server local time.
Solution: Force UTC for all internal logic (core/timestamps.py). Convert only at display time (Excel/Dashboard).
3.2 Performance (N+1 Queries)
Problem: Fetching 100 members = 100*50 Boss Queries.
Solution: Use SQLAlchemy joinedload to fetch User+Snapshots+Bosses in single efficient queries.
3.3 Observability
Problem: "It stalled." -> "Where?"
Solution:
Add structlog or standard logging with trace_id.
Log every standard "Checkpoint" in main.py (Harvest Start, Harvest End, Report Start...).