# ⚙️ Recommended Upgrades: Backend Architecture & Performance

Focused purely on improving the efficiency, reliability, and scalability of the Python/SQL backend.

## 1. SQLite WAL Mode (Concurrency Boost)

* **The Issue**: The database currently uses the default Rollback Journal mode. If the Harvester is writing, the Web Dashboard (or Reporter) cannot read, causing "Database Locked" errors.
* **The Upgrade**: Execute `PRAGMA journal_mode=WAL;` on initialization.
* **Benefit**: Readers (Dashboard) no longer block Writers (Harvest). Massive concurrency improvement.

## 2. AsyncIO Database Driver (`aiosqlite`)

* **The Issue**: `harvest.py` is an asynchronous script (`async def`), but it calls synchronous, blocking database methods (`db.commit()`), effectively pausing the entire event loop.
* **The Upgrade**: Switch to `SQLAlchemy 2.0`'s `AsyncSession` with the `aiosqlite` driver.
* **Benefit**: The Harvester can fetch from Discord/WOM *while* saving records to the DB simultaneously. 2x-3x speedup on large harvests.

## 3. "Cold Storage" Archival Strategy

* **The Issue**: `clan_data.db` grows indefinitely. Queries for "Last 7 Days" needlessly scan year-old data.
* **The Upgrade**: A maintenance script that moves snapshots older than 180 days to `clan_data_archive.db` and runs `VACUUM`.
* **Benefit**: Keeps the "Hot" DB small and fast. Reports generate in seconds instead of minutes.

## 4. Pydantic Data Validation

* **The Issue**: Currently, JSON from APIs is parsed with raw dictionary lookups (`data.get('skills', {})...`). This is fragile and error-prone.
* **The Upgrade**: Define strict Pydantic models (`class WomSnapshot(BaseModel)`) that validate data structure *before* it hits the logic layer.
* **Benefit**: Eliminates "NoneType" crashes; catches API changes immediately with clear error messages.

## 5. Watchdog Health Service

* **The Issue**: If the harvest script crashes silently, you might not know for days until you see an empty dashboard.
* **The Upgrade**: A standalone "Watchdog" process that checks the DB's `last_updated` timestamp. If > 24h, it triggers a Discord Webhook alert.
* **Benefit**: "Set and forget" peace of mind.

## 6. Alembic Auto-Migrations

* **The Issue**: Schema changes currently require manual SQL or deleting the DB.
* **The Upgrade**: Fully configure Alembic to auto-generate migration scripts based on changes to `models.py`.
* **Benefit**: Safely add new features (e.g., "Economy Tracking" tables) without deleting history or losing data.

## 7. Robust Configuration (`pydantic-settings`)

* **The Issue**: `core/config.py` relies on `os.getenv` with manual type casting, leading to potential silent misconfigurations.
* **The Upgrade**: Use `pydantic-settings` to define a schema for your `.env` file.
* **Benefit**: Failure to start if critical config (like API Keys) is missing or malformed, preventing runtime errors.

## 8. Integrated Job Scheduler (`APScheduler`)

* **The Issue**: Reliance on external `.bat` files or Windows Task Scheduler is clunky for complex dependencies.
* **The Upgrade**: Integrate `APScheduler` directly into `main.py` to run Harvest (Hourly), Report (Weekly), and Cleanup (Monthly) in a single Python process.
* **Benefit**: Cross-platform reliability; "One click run" experience.
