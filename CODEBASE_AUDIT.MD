# ClanStats: Senior PhD Technical Audit Report

## 1. Architectural Friction: "The Subprocess Tax"

The project enforces a **Process Isolation** strategy where `main.py` orchestrates the pipeline via `subprocess.Popen`.

- **The Issue**: Every stage (Harvest, Enrich, Report, Export) is forced to perform its own cold start, including re-initializing DB connections and re-loading configurations.
- **The Impact**: This prevents the use of a unified SQLAlchemy session/unit-of-work. It necessitates the "dual database access pattern" seen in `harvest_sqlite.py`, where raw `sqlite3` is used alongside ORM-based services to avoid connection/locking issues created by the isolation itself.

## 2. Duplicate AI Brains

There is significant logic duplication between `scripts/mcp_enrich.py` and `scripts/ai_analyst.py`.

- **The Issue**: Both scripts independently calculate "active player" lists, message counts, and "Social Value" by querying `wom_records` and `discord_messages`.
- **The Impact**: Maintaining two separate sets of SQL queries for the "Top XP" or "Silent Grinder" logic increases the surface area for bugs (e.g., one script using a 7-day window while the other uses 30-day).

## 3. Speculative Overengineering (Dead Code)

`core/analytics.py` contains roughly 200 lines of "Phase 2.2.2+" code.

- **The Issue**: Methods like `get_latest_snapshots_by_id` and `get_gains_by_id` are implemented for an ID-based schema that doesn't fully exist yet (noted as "Requires: user_id FK populated").
- **The Impact**: You are essentially maintaining a "ghost service" within the production analytics layer, which clutters the API and increases cognitive load for future developers.

## 4. Brittle Package Hygiene

The use of `sys.path.append(os.getcwd())` and `sys.path.insert(0, ...)` is ubiquitous across `scripts/` and `tests/`.

- **The Issue**: The project is structured as a collection of loose scripts rather than an installable Python package.
- **The Impact**: This makes the codebase fragile to the execution context (CWD). Moving a script or running it from a different directory will likely cause import failures.

## 5. Inconsistent Persistence Logic

Data harvesting and storage is a mix of paradigms:

- **Harvest Logic**: `harvest_sqlite.py` iterates over members and merges data using raw `cursor.execute` and manual state tracking in a separate `data/harvest_state.json`.
- **Analytics Logic**: Uses SQLAlchemy with complex window functions and windowed queries.
- **The Bad Habit**: Split state (JSON + SQLite). The "last checked" timestamp for a player belongs in the database, not a sidecar JSON file.

## 6. Logic Hardcoding (Data belongs in DB)

The `LEADERSHIP_ROSTER` in `mcp_enrich.py` and various "lore" snippets are hardcoded strings inside Python files.

- **The Issue**: Changes to clan staff require a code deployment rather than a database/config update.
- **The Impact**: This breaks the "Database as the Central Bus" philosophy mentioned in `GEMINI.md`.

## 7. Performance Bottleneck: strftime on 1.3GB

The `AnalyticsService.get_activity_heatmap` query uses `strftime` inside the group-by clause.

- **The Issue**: Even with indexes, formatting every row in a massive table during the query is expensive.
- **The Better Habit**: Store the Day-of-Week and Hour as indexed integer columns at ingestion time to keep the heatmap query O(1) relative to total row count.

## 8. Verification Quality Note

The claim of "145/145 passing tests" is high, but the test suite relies heavily on Mocks (`MockWOMClient`) and VCR cassettes.

- **The Finding**: There is a lack of end-to-end integration tests that verify the *actual* analytics output against a real (temporary) database with known edge cases. The tests verify that the *pipes* work, but not necessarily that the *math* is always correct across complex time windows.

## 9. Complexity Hazard: `process_wom_harvest`

This function is a 230-line "God Function" in `harvest_sqlite.py`. It handles networking, JSON parsing, member synchronization, state management, and bulk DB inserts. It violates the Single Responsibility Principle and is significantly harder to unit test than broken-down components.

<hr>

## 10. Performance Audit

The system handles a 1.3GB dataset effectively but shows signs of "Premature Pessimization" and "Unoptimized Bulk Operations":

- **Subprocess Overhead**: The "Process Isolation" architecture forces the Python interpreter to start 4-5 times per pipeline run. This adds ~1-2 seconds of dead time per step (fetching imports, initializing allocators).
- **JSON Parsing at Scale**: The `raw_data` column in `wom_snapshots` is stored as TEXT. Queries like `get_skill_mastery` parse this JSON string in Python *for every matching row*. As the dataset grows, this O(N) deserialization will become the dominant CPU cost.
- **N+1 Query Patterns**: While `AnalyticsService` has some bulk methods, the `harvest_sqlite.py` script performs `resolve_member_id_sqlite` individually inside the harvest loop. For 500+ members, this is 500 unnecessary DB round-trips that could be a single `WHERE username IN (...)` query.
- **Memory Pressure**: `report_sqlite.py` loads `latest_snaps` (all users) into memory dictionaries. With the 1.3GB DB size, scaling to thousands of users might exhaust standard container memory limits (512MB/1GB).

## 11. Top 10 Recommended Improvements

1. **Consolidate Entry Point**: Replace `subprocess.Popen` in `main.py` with direct function calls to `run()` methods in each module. This shares the DB connection pool and eliminates cold starts.
2. **Schema Normalization**: Add `hour` (int) and `day_of_week` (int) columns to `discord_messages`. Populate them at insert time to make the Heatmap query O(1) complexity (index scan) instead of O(N) scan + format.
3. **JSON Shredding**: Create a `snapshot_skills` table. Extract key stats (Total XP, EHP, Level 99s) during ingestion. Isolate `raw_data` effectively as "Cold Storage" that is rarely queried.
4. **Async Ingestion Pipeline**: Refactor `harvest_sqlite.py` to use `aiosqlite`. Pipeline the "Fetch -> Parse -> Insert" stages so network latency is hidden by DB I/O (and vice-versa).
5. **Unified State Management**: Migrate the `data/harvest_state.json` data into a `harvest_log` table in SQLite. This ensures transactional integrity (state is only updated if data is committed).
6. **Code De-Duplication**: Refactor `ai_analyst.py` to import and use `AnalyticsService` for all data fetching. Delete the duplicate ad-hoc SQL queries.
7. **Dynamic Configuration**: Move `LEADERSHIP_ROSTER` and Clan Lore to a `clan_settings` table or a generic `config` table in the DB.
8. **Package Restructure**: Add a `setup.py` and `src/` directory. Install the project in editable mode (`pip install -e .`) to resolve import issues permanently without `sys.path` hacks.
9. **Integration Test Suite**: Create a `tests/integration/test_full_pipeline.py` that spins up a temporary 10MB SQLite DB, runs the full Harvest->Report cycle, and asserts that the Excel file contains expected rows.
10. **Cold Storage Strategy**: Implement a monthly "cleanup" script that aggregates snapshots older than 1 year into weekly averages and deletes the raw daily rows to keep the DB size under 2GB.
