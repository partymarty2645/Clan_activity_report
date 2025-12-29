import sys
import os
import asyncio
import json
import sqlite3
import datetime
from datetime import timezone
from typing import Optional


from services.wom import WOMClient
from services.discord import DiscordFetcher
from services.factory import ServiceFactory
from services.identity_service import resolve_member_by_name
from core.config import Config
from core.usernames import UsernameNormalizer
from core.timestamps import TimestampHelper
from data.queries import Queries
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

import logging

# Configure Logging to STDOUT for real-time visibility in main.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Module-level logger for this script
logger = logging.getLogger("harvest_sqlite")

console = Console()

DB_PATH = "clan_data.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def _extract_joined_at(member: dict) -> Optional[str]:
    """
    Extract an ISO timestamp for when a member joined, accepting either
    'joinedAt' (camelCase) or 'joined_at' (snake_case) from upstream data.

    Returns ISO 8601 string or None if unavailable/unparseable.
    """
    joined_at_str = member.get('joinedAt') or member.get('joined_at')
    if not joined_at_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(joined_at_str.replace('Z', '+00:00'))
        dt = TimestampHelper.to_utc(dt)
        # If joined date is in the future, ignore it (invalid data)
        if dt is None or dt > datetime.datetime.now(timezone.utc):
            return None
        return dt.isoformat() if dt else None
    except Exception:
        return None

def resolve_member_id_sqlite(cursor: sqlite3.Cursor, normalized_name: str) -> Optional[int]:
    """
    Resolve a member_id using the same sqlite connection to avoid ORM locking.

    Prefers alias lookup (player_name_aliases.normalized_name) and falls back to
    clan_members.username if no alias exists.
    """
    if not normalized_name:
        return None

    try:
        cursor.execute("SELECT member_id FROM player_name_aliases WHERE normalized_name = ?", (normalized_name,))
        row = cursor.fetchone()
        if row and row[0] is not None:
            return row[0]
    except Exception as alias_err:
        logger.debug(f"Alias lookup failed for {normalized_name}: {alias_err}")

    try:
        cursor.execute("SELECT id FROM clan_members WHERE username = ?", (normalized_name,))
        row = cursor.fetchone()
        if row and row[0] is not None:
            return row[0]
    except Exception as member_err:
        logger.debug(f"Member lookup failed for {normalized_name}: {member_err}")

    return None

def get_latest_snapshot_timestamp(cursor: sqlite3.Cursor, username: str) -> Optional[str]:
    """
    Get the latest snapshot timestamp for a player to enable incremental fetching.
    Returns ISO 8601 timestamp string or None if no snapshots exist.
    """
    try:
        cursor.execute("SELECT MAX(timestamp) FROM wom_snapshots WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        return None
    except Exception as e:
        logger.debug(f"Failed to get latest timestamp for {username}: {e}")
        return None

async def fetch_member_data(username, wom=None, start_date: Optional[str] = None):
    try:
        # Use injected WOM client or get from ServiceFactory
        client = wom if wom is not None else await ServiceFactory.get_wom_client()
        # Fetch snapshots (incremental if start_date provided, else full history)
        if start_date:
            snapshots = await client.get_player_snapshots(username, start_date=start_date)
        else:
            snapshots = await client.get_player_snapshots(username)
        return (username, snapshots)
    except Exception as e:
        logger.warning(f"Failed to fetch {username}: {e}")
        return (username, None)

async def fetch_and_check_staleness(username, wom=None):
    # Wrapper to fetch details, check staleness, and optionally update
    try:
        # Use injected WOM client or get from ServiceFactory
        client = wom if wom is not None else await ServiceFactory.get_wom_client()
        p = await client.get_player_details(username)
        if not p: return (username, None)
        
        # Check staleness
        updated_at_str = p.get('updatedAt')
        if updated_at_str:
            last_update = datetime.datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            now = datetime.datetime.now(timezone.utc)
            if (now - last_update).total_seconds() > Config.HARVEST_STALE_THRESHOLD_SECONDS:
                # Trigger update
                print(f"  [Stale] {username} last updated {last_update}. Requesting scan...")
                try:
                    await client.update_player(username)
                    # We could re-fetch, but let's just use current data for now to avoid stalling
                    # The update will happen in background on WOM side usually? 
                    # WOM update is sync or async? It returns new data usually.
                    # Let's try to re-fetch or assume next run gets it.
                except Exception as e:
                    print(f"  Failed to request update for {username}: {e}")
        
        return (username, p)
    except Exception as e:
        return (username, None)

async def run_sqlite_harvest(wom_client_inject: Optional[WOMClient] = None, discord_service_inject: Optional[DiscordFetcher] = None):
    # Use injected clients or get from ServiceFactory
    wom = wom_client_inject if wom_client_inject is not None else await ServiceFactory.get_wom_client()
    discord = discord_service_inject if discord_service_inject is not None else await ServiceFactory.get_discord_service()
    
    print(f"Connecting to {DB_PATH} via sqlite3...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- PHASE 0: GROUP UPDATE (Requested by User) ---
    try:
        secret = Config.WOM_GROUP_SECRET
        if secret:
            print(f"Initiating clan-wide data refresh on Wise Old Man (Group ID: {Config.WOM_GROUP_ID})...")
            # We use the update_group method which hits /groups/{id}/update-all
            await wom.update_group(Config.WOM_GROUP_ID, secret)
            print("Request acknowledged by WOM. Scanning all members...")
            
            wait_time = Config.WOM_UPDATE_WAIT
            print(f"Waiting {wait_time}s for WOM to update remote profiles...")
            
            # Simple countdown for user feedback
            for i in range(wait_time, 0, -5):
                # Only print specific intervals to reduce noise in main pipeline
                if i % 15 == 0:
                    print(f"  ... {i}s remaining")
                await asyncio.sleep(5)
                
            print("Remote update window closed. Proceeding to download.")
        else:
            print("Skipping global update (WOM_GROUP_SECRET not set). Using existing cloud data.")
    except Exception as e:
        print(f"Global update skipped: {e}. continuing with local/cached data.")


    # --- PREPARE DISCORD START DATE ---
    discord_start_date = None
    try:
        cursor.execute(Queries.GET_LAST_MSG_DATE)
        last_msg_row = cursor.fetchone()
        last_msg_ts = last_msg_row[0] if last_msg_row else None
        
        founding_date = Config.CLAN_FOUNDING_DATE
        
        if last_msg_ts:
            if isinstance(last_msg_ts, str):
                last_msg_ts = last_msg_ts.replace(' ', 'T')
                try:
                    if '+' not in last_msg_ts and 'Z' not in last_msg_ts:
                        last_msg_ts += '+00:00'
                    start_date = datetime.datetime.fromisoformat(last_msg_ts)
                    start_date = TimestampHelper.to_utc(start_date)
                    if start_date is not None:
                        start_date = start_date + datetime.timedelta(milliseconds=1)
                        print(f"  - Found previous messages. Resuming from {TimestampHelper.format_for_display(start_date)}...")
                        discord_start_date = start_date
                    else:
                        discord_start_date = founding_date
                except:
                    discord_start_date = founding_date
            else:
                discord_start_date = founding_date
        else:
            print("  - No previous messages found. fetching from Clan Founding (Feb 14, 2025)...")
            discord_start_date = founding_date

    except Exception as e:
        print(f"  - Error checking last message: {e}. Defaulting to Founding Date.")
        discord_start_date = datetime.datetime(2025, 2, 14, tzinfo=timezone.utc)


    # --- DEFINE PARALLEL TASKS ---
    
    async def task_wom_harvest():
        try:
            print("[Parallel] Starting WOM Harvest...")
            await process_wom_harvest(wom, conn, cursor)
            print("[Parallel] WOM Harvest Complete.")
        except Exception as e:
            print(f"WOM Harvest Failed: {e}")
            logger.exception("WOM Harvest Error")

    async def task_discord_harvest():
        try:
            print(f"[Parallel] Starting Discord Harvest (From {discord_start_date})...")
            await discord.fetch(start_date=discord_start_date)
            print("[Parallel] Discord Harvest Complete.")
        except Exception as e:
            print(f"Discord Harvest Failed: {e}")
            logger.exception("Discord Harvest Error")

    # --- EXECUTE PARALLEL ---
    print("🚀 Launching Parallel Harvest Tasks (WOM & Discord)...")
    try:
        await asyncio.gather(task_wom_harvest(), task_discord_harvest())
        print("✅ Parallel Harvest Finished.")
    finally:
        # Clean up resources properly
        print("Cleaning up resources...")
        
        if conn:
            try:
                conn.close()
                print("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

        # Ensure service cleanup even on interruption
        if wom_client_inject is None or discord_service_inject is None:
            try:
                await ServiceFactory.cleanup()
                print("Services cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up services: {e}")

    

async def process_wom_harvest(wom, conn, cursor):
    # 1. Get Members
    print("Downloading latest member roster from WOM...")
    members = await wom.get_group_members(Config.WOM_GROUP_ID)
    print(f"Roster downloaded: {len(members)} active members found.")
    
    # Limit for testing if needed
    # members = members[:10] 
    
    # --- MEMBER SYNC (Source of Truth) ---
    print(f"Synchronizing local database with remote roster...")
    active_usernames = []
    rows_to_upsert = []
    
    ts_now_dt = TimestampHelper.now_utc()
    ts_now_iso = ts_now_dt.isoformat()

    for m in members:
        # WOM API returns keys like 'username', 'role', 'joinedAt'
        raw_name = m.get('username', '')
        if not raw_name: continue
        
        u_clean = UsernameNormalizer.normalize(raw_name)
        active_usernames.append(u_clean)
        
        role = m.get('role', 'member')
        # Supports either 'joinedAt' (camelCase) or 'joined_at' (snake_case)
        joined_iso = _extract_joined_at(m)
        rows_to_upsert.append((u_clean, role, joined_iso, ts_now_iso))

    try:
        # 1. UPSERT (Insert or Replace)
        # Using INSERT OR REPLACE requires a UNIQUE/PRIMARY KEY on username, which we have.
        cursor.executemany(Queries.UPSERT_MEMBER, rows_to_upsert)
        
        # 2. DELETE Stale Members (With Safe-Fail Threshold)
        # Remove anyone in DB who is NOT in the active_usernames list
        if active_usernames:
            placeholders = ','.join('?' * len(active_usernames))
            
            # Safe-Fail Check
            cursor.execute(Queries.SELECT_MEMBER_COUNT)
            total_db_members = cursor.fetchone()[0]
            
            if total_db_members > 0:
                potential_deletes = total_db_members - len(active_usernames) # Rough estimate or check distinct
                # Better: Check how many WOULD be deleted
                cursor.execute(Queries.SELECT_MEMBERS_TO_DELETE.format(placeholders), active_usernames)
                would_delete = cursor.fetchone()[0]
                
                delete_ratio = would_delete / total_db_members
                
                if delete_ratio > Config.HARVEST_SAFE_DELETE_RATIO:
                    print(f"CRITICAL WARNING: Harvest would delete {would_delete} members ({delete_ratio:.1%}). Aborting deletion for safety.")
                    # We continue without deleting
                else:
                     sql_del = Queries.DELETE_STALE_MEMBERS.format(placeholders)
                     cursor.execute(sql_del, active_usernames)
                     deleted_count = cursor.rowcount
                     print(f"Synced Members: Updated {len(rows_to_upsert)}, Deleted {deleted_count} stale/banned members.")
            else:
                 # Initial population
                 pass
        
        conn.commit()
    except Exception as e:
        print(f"Error syncing members: {e}")
        
    # OPTIMIZATION: Only fetch snapshots AFTER the latest stored timestamp for each player
    # This reduces API load from ~600K requests/run to ~1-2K for incremental updates
    # ADDITIONAL OPTIMIZATION: Skip players with recent snapshots (< threshold hours old)
    tasks = []
    now_utc = datetime.datetime.now(timezone.utc)
    staleness_threshold_seconds = Config.WOM_STALENESS_SKIP_HOURS * 3600
    skipped_count = 0
    
    # Skip staleness optimization if WOM_STALENESS_SKIP_HOURS is 0
    if Config.WOM_STALENESS_SKIP_HOURS == 0:
        staleness_threshold_seconds = float('inf')  # Never skip based on staleness
    
    for m in members:
        username = m['username']
        latest_ts = get_latest_snapshot_timestamp(cursor, username)
        
        if latest_ts:
            # Parse timestamp and check if data is fresh
            try:
                latest_dt = datetime.datetime.fromisoformat(latest_ts.replace('Z', '+00:00'))
                age_seconds = (now_utc - latest_dt).total_seconds()
                
                if age_seconds < staleness_threshold_seconds:
                    # Data is fresh, skip fetching
                    skipped_count += 1
                    continue
            except:
                pass
            
            # Player has history: fetch only NEW snapshots since last stored timestamp
            tasks.append(fetch_member_data(username, wom=wom, start_date=latest_ts))
        else:
            # New player: fetch full history
            tasks.append(fetch_member_data(username, wom=wom))
    # Determine if we are running in an interactive terminal
    # is_interactive = sys.stdout.isatty() and not os.environ.get("NO_RICH")
    is_interactive = False
    
    # Initialize results list to store member data
    results = []
    
    # Log optimization impact
    if skipped_count > 0:
        hours_threshold = Config.WOM_STALENESS_SKIP_HOURS
        print(f"Skipped {skipped_count} players with recent data (< {hours_threshold}h old). Fetching {len(tasks)} players...")
    else:
        print(f"Downloading player snapshots ({len(tasks)} in queue)...")
    
    try:
        if is_interactive:
            # Removed Progress Bar for Parallel safety (console conflict likely)
             print(f"Downloading player snapshots ({len(tasks)} in queue)...")
             for f in asyncio.as_completed(tasks):
                res = await f
                results.append(res)
        else:
            # Non-interactive mode (e.g. piped to main.py)
            print(f"Downloading player snapshots ({len(tasks)} in queue)...")
            completed_count = 0
            for f in asyncio.as_completed(tasks):
                res = await f
                results.append(res)
                completed_count += 1
                if completed_count % 10 == 0:
                    print(f"  Processed {completed_count}/{len(tasks)} players...")
                    sys.stdout.flush() # Force flush to ensure main.py sees it immediately
                
        print("Saving to Database...")
        
        # Prepare data for bulk insert
        snapshot_inserts = [] 
        
        count_snaps = 0
        count_bosses = 0
        
        ts_now = datetime.datetime.now(timezone.utc)
        
        # Note: Member ID resolution skipped due to dual database access pattern
        for username, data in results:
                if not data: continue
                
                u_clean = UsernameNormalizer.normalize(username)
                
                for snap in data:
                    snap_data = snap.get('data', {})
                    created_at = snap.get('createdAt')
                    if not created_at: continue
                    
                    try:
                        ts_dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        ts_dt = TimestampHelper.to_utc(ts_dt)
                        if ts_dt is None:
                            continue
                        ts_now_iso = ts_dt.isoformat()
                    except:
                        continue
                    
                    skills = snap_data.get('skills', {})
                    bosses = snap_data.get('bosses', {})
                    
                    xp = skills.get('overall', {}).get('experience', 0)
                    total_boss = sum(b.get('kills', 0) for b in bosses.values() if b.get('kills', 0) > 0)
                    
                    raw_json = json.dumps(snap)
                    
                    member_id = resolve_member_id_sqlite(cursor, u_clean)
                    
                    try:
                        cursor.execute(Queries.INSERT_SNAPSHOT, (u_clean, ts_now_iso, xp, total_boss, 0, 0, raw_json, member_id))
                        
                        snap_id = cursor.lastrowid
                        count_snaps += 1
                        
                        boss_rows = []
                        for b_name, b_val in bosses.items():
                            kills = b_val.get('kills', -1)
                            rank = b_val.get('rank', 0)
                            if kills > -1:
                                boss_rows.append((snap_id, b_name, kills, rank))
                        
                        if boss_rows:
                            cursor.executemany(Queries.INSERT_BOSS_SNAPSHOT, boss_rows)
                            count_bosses += len(boss_rows)
                            
                    except Exception as e:
                        if "UNIQUE constraint failed" in str(e):
                            pass
                        else:
                            print(f"Error saving {u_clean}: {e}")

        conn.commit()
        print(f"Done. Saved {count_snaps} snapshots and {count_bosses} boss records.")

    except Exception as e:
        print(f"Error during WOM Snapshot Processing: {e}")
        logger.exception("WOM Snapshot Error")



    # --- IDENTITY SYNC: Skipped to avoid database lock issues ---
    # Identity resolution now uses the same sqlite connection to avoid ORM locks.
    # Alias linkage is resolved inline when snapshots are saved.
    print("Identity resolution performed via sqlite alias lookup")

if __name__ == "__main__":
    asyncio.run(run_sqlite_harvest())
