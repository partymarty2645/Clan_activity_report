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
from database.connector import SessionLocal
from services.user_access_service import UserAccessService
from core.config import Config
from core.performance import timed_operation
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

from database.connector import SessionLocal

# DEPRECATED: Use get_db_session() instead
def get_db_connection():
    """Legacy function - use get_db_session() for new code"""
    return sqlite3.connect(Config.DB_FILE)

def get_db_session():
    """Get a SQLAlchemy session with proper context management"""
    return SessionLocal()

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
    Resolve a member_id using UserAccessService with fallback to direct sqlite queries.

    Prefers UserAccessService for consistent resolution across the application,
    then falls back to alias lookup (player_name_aliases.normalized_name) and 
    clan_members.username if needed.
    """
    if not normalized_name:
        return None

    # Try UserAccessService first for consistent resolution
    try:
        session = SessionLocal()
        user_service = UserAccessService(session)
        user_id = user_service.resolve_user_id(normalized_name)
        session.close()
        if user_id:
            return user_id
    except Exception as e:
        logger.debug(f"UserAccessService resolution failed for {normalized_name}: {e}")

    # Fallback to direct database queries
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
    
    print(f"Connecting to {Config.DB_FILE} via SQLAlchemy...")
    db_session = get_db_session()
    
    # Keep legacy sqlite3 connection for compatibility during transition
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
    except asyncio.CancelledError:
        print("Harvest tasks cancelled by user.")
        raise
    except Exception as e:
        print(f"Harvest tasks failed: {e}")
        logger.exception("Harvest execution error")
        raise
    finally:
        # Clean up resources properly (services cleanup MUST happen after tasks complete)
        print("Cleaning up resources...")
        
        # Note: db_session is managed inside process_wom_harvest(), not here
        
        if conn:
            try:
                conn.close()
                print("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

        # Ensure service cleanup (close aiohttp sessions)
        if wom_client_inject is None or discord_service_inject is None:
            try:
                await ServiceFactory.cleanup()
                print("Services cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up services: {e}")

    

async def process_wom_harvest(wom, conn, cursor):
    """
    REFACTORED: Now uses pure SQLAlchemy ORM instead of raw sqlite3.
    conn/cursor parameters kept for compatibility but not used.
    """
    from database.connector import SessionLocal
    from database.models import ClanMember, WOMSnapshot, BossSnapshot
    from sqlalchemy import select, func, delete
    
    # Get ORM session
    db_session = SessionLocal()
    
    try:
        # 1. Get Members
        print("Downloading latest member roster from WOM...")
        members = await wom.get_group_members(Config.WOM_GROUP_ID)
        print(f"Roster downloaded: {len(members)} active members found.")
        
        # --- MEMBER SYNC (Source of Truth) ---
        print(f"Synchronizing local database with remote roster...")
        active_usernames = []
        ts_now_dt = TimestampHelper.now_utc()
        ts_now_iso = ts_now_dt.isoformat()

        for m in members:
            raw_name = m.get('username', '')
            if not raw_name: continue
            
            u_clean = UsernameNormalizer.normalize(raw_name)
            active_usernames.append(u_clean)
            
            role = m.get('role', 'member')
            joined_iso = _extract_joined_at(m)
            
            # UPSERT via SQLAlchemy
            existing = db_session.execute(
                select(ClanMember).where(ClanMember.username == u_clean)
            ).scalar_one_or_none()
            
            if existing:
                existing.role = role
                # existing.last_updated is NOT updated here, only on successful snapshot fetch
                if joined_iso and not existing.joined_at:
                    existing.joined_at = datetime.datetime.fromisoformat(joined_iso.replace('Z', '+00:00'))
            else:
                new_member = ClanMember(
                    username=u_clean,
                    role=role,
                    joined_at=datetime.datetime.fromisoformat(joined_iso.replace('Z', '+00:00')) if joined_iso else None,
                    last_updated=None # Will be set upon first successful snapshot fetch
                )
                db_session.add(new_member)
        
        # 2. DELETE Stale Members (With Safe-Fail Threshold)
        if active_usernames:
            total_db_members = db_session.execute(
                select(func.count()).select_from(ClanMember)
            ).scalar()
            
            if total_db_members > 0:
                would_delete = db_session.execute(
                    select(func.count()).select_from(ClanMember).where(
                        ClanMember.username.notin_(active_usernames)
                    )
                ).scalar()
                
                delete_ratio = would_delete / total_db_members
                
                if delete_ratio > Config.HARVEST_SAFE_DELETE_RATIO:
                    print(f"CRITICAL WARNING: Harvest would delete {would_delete} members ({delete_ratio:.1%}). Aborting deletion for safety.")
                else:
                    deleted = db_session.execute(
                        delete(ClanMember).where(ClanMember.username.notin_(active_usernames))
                    )
                    deleted_count = deleted.rowcount
                    print(f"Synced Members: Updated {len(active_usernames)}, Deleted {deleted_count} stale/banned members.")
        
        db_session.commit()
        
<<<<<<< HEAD
    # --- LOAD HARVEST STATE ---
    STATE_FILE = "data/harvest_state.json"
    harvest_state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                harvest_state = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load harvest state: {e}")

    # OPTIMIZATION: Check 'last_api_check' from local state to avoid spamming WOM for inactive users
    tasks = []
    now_utc = datetime.datetime.now(timezone.utc)
    skipped_count = 0
    
    # Enable staleness check only if WOM_STALENESS_SKIP_HOURS > 0
    use_staleness_optimization = Config.WOM_STALENESS_SKIP_HOURS > 0
    staleness_threshold_seconds = Config.WOM_STALENESS_SKIP_HOURS * 3600 if use_staleness_optimization else 0
    
    # List of users we intend to update in state
    users_processed_in_this_run = []

    for m in members:
        username = m['username']
        
        # Check explicit API staleness (When did we last ASK Wom?)
        if use_staleness_optimization:
            last_check_iso = harvest_state.get(username)
            if last_check_iso:
                try:
                    last_check_dt = datetime.datetime.fromisoformat(last_check_iso)
                    # Handle TZ naive/aware mismatch if needed (isoformat usually preserves it)
                    if last_check_dt.tzinfo is None:
                         last_check_dt = last_check_dt.replace(tzinfo=timezone.utc)
                         
                    age_seconds = (now_utc - last_check_dt).total_seconds()
                    
                    if age_seconds < staleness_threshold_seconds:
                        # We checked this user recently (whether they had data or not)
                        skipped_count += 1
                        continue
                except Exception as e:
                    # If parse error, assume stale and fetch
                    pass

        # If we are here, we are going to fetch.
        # Track this username to update the state file later
        users_processed_in_this_run.append(username)

        # Still use latest_ts to fetch INCREMENTAL data (optimization #2)
        latest_ts = get_latest_snapshot_timestamp(cursor, username)
        
        if latest_ts:
             tasks.append(fetch_member_data(username, wom=wom, start_date=latest_ts))
        else:
             tasks.append(fetch_member_data(username, wom=wom))
            
    # Determine if we are running in an interactive terminal
    # is_interactive = sys.stdout.isatty() and not os.environ.get("NO_RICH")
    is_interactive = False
    
    # Initialize results list to store member data
    results = []
    
    # Log optimization impact
    if skipped_count > 0:
        hours_threshold = Config.WOM_STALENESS_SKIP_HOURS
        print(f"Skipped {skipped_count} players (Checked < {hours_threshold}h ago). Fetching {len(tasks)} players...")
    else:
        print(f"Downloading player snapshots ({len(tasks)} in queue)...")
    
    try:
=======
        # OPTIMIZATION: Check Staleness via ClanMember.last_updated
        tasks = []
        now_utc = datetime.datetime.now(timezone.utc)
        skipped_count = 0
        
        use_staleness_optimization = Config.WOM_STALENESS_SKIP_HOURS > 0
        staleness_threshold_seconds = Config.WOM_STALENESS_SKIP_HOURS * 3600 if use_staleness_optimization else 0
        
        for m in members:
            username = m['username']  # Use raw username for WOM API (case-sensitive)
            username_normalized = UsernameNormalizer.normalize(username)  # Normalize for DB lookups
            
            # Check Member's last_updated
            member = db_session.execute(
                select(ClanMember).where(ClanMember.username == username_normalized)
            ).scalar_one_or_none()
            
            should_fetch = True
            latest_ts = None
            
            # Get latest snapshot timestamp for start_date optimization
            # (We still need this to incremental fetch, but NOT for staleness check)
            latest_snap = db_session.execute(
                select(WOMSnapshot)
                .where(WOMSnapshot.username == username_normalized)
                .order_by(WOMSnapshot.timestamp.desc())
                .limit(1)
            ).scalar_one_or_none()
            latest_ts = latest_snap.timestamp.isoformat() if latest_snap else None

            if use_staleness_optimization and member and member.last_updated:
                try:
                    # Check if our own scan is recent
                    last_scan_dt = member.last_updated
                    if last_scan_dt.tzinfo is None:
                        last_scan_dt = last_scan_dt.replace(tzinfo=timezone.utc)
                        
                    age_seconds = (now_utc - last_scan_dt).total_seconds()
                    
                    if age_seconds < staleness_threshold_seconds:
                        skipped_count += 1
                        should_fetch = False
                except Exception as e:
                    logger.debug(f"Error Checking staleness for {username}: {e}")
                    pass
            
            if should_fetch:
                tasks.append(fetch_member_data(username, wom=wom, start_date=latest_ts))

        
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
        
>>>>>>> fix/cleanup
        if is_interactive:
            # Removed Progress Bar for Parallel safety (console conflict likely)
            print(f"Downloading player snapshots ({len(tasks)} in queue)...")
            for f in asyncio.as_completed(tasks):
                res = await f
                results.append(res)
        else:
            # Non-interactive mode (e.g. piped to main.py)
            completed_count = 0
            for f in asyncio.as_completed(tasks):
                res = await f
                results.append(res)
                completed_count += 1
                if completed_count % 10 == 0:
                    print(f"  Processed {completed_count}/{len(tasks)} players...")
                    sys.stdout.flush() # Force flush to ensure main.py sees it immediately
        
        print("Saving to Database...")
        
        count_snaps = 0
        count_bosses = 0
        
        ts_now_iso_state = now_utc.isoformat()
        
        # Update State for all processed users (success or not, we TRIED)
        for u in users_processed_in_this_run:
            harvest_state[u] = ts_now_iso_state
            
        # Save State File
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(harvest_state, f, indent=2)
            print(f"Updated harvest state for {len(users_processed_in_this_run)} users.")
        except Exception as e:
            print(f"Failed to save harvest state: {e}")

        
        # Process results using ORM
        for username, data in results:
            if not data: continue
            
            u_clean = UsernameNormalizer.normalize(username)
            
            # Get member_id via ORM
            member = db_session.execute(
                select(ClanMember).where(ClanMember.username == u_clean)
            ).scalar_one_or_none()
            
            member_id = member.id if member else None
            
            for snap in data:
                snap_data = snap.get('data', {})
                created_at = snap.get('createdAt')
                if not created_at: continue
                
                try:
                    ts_dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    ts_dt = TimestampHelper.to_utc(ts_dt)
                    if ts_dt is None:
                        continue
                except:
                    continue
                
                skills = snap_data.get('skills', {})
                bosses = snap_data.get('bosses', {})
                
                xp = skills.get('overall', {}).get('experience', 0)
                total_boss = sum(b.get('kills', 0) for b in bosses.values() if b.get('kills', 0) > 0)
                
                raw_json = json.dumps(snap)
                
                # Check if snapshot already exists (UNIQUE constraint)
                existing_snap = db_session.execute(
                    select(WOMSnapshot).where(
                        WOMSnapshot.username == u_clean,
                        WOMSnapshot.timestamp == ts_dt
                    )
                ).scalar_one_or_none()
                
                if existing_snap:
                    continue  # Skip duplicates
                
                try:
                    new_snap = WOMSnapshot(
                        username=u_clean,
                        timestamp=ts_dt,
                        total_xp=xp,
                        total_boss_kills=total_boss,
                        ehp=0,
                        ehb=0,
                        raw_data=raw_json,
                        user_id=member_id
                    )
                    db_session.add(new_snap)
                    db_session.flush()  # Get the ID
                    
                    count_snaps += 1
                    
                    # Insert boss snapshots
                    for b_name, b_val in bosses.items():
                        kills = b_val.get('kills', -1)
                        rank = b_val.get('rank', 0)
                        if kills > -1:
                            boss_snap = BossSnapshot(
                                snapshot_id=new_snap.id,
                                boss_name=b_name,
                                kills=kills,
                                rank=rank
                            )
                            db_session.add(boss_snap)
                            count_bosses += 1
            
                    # Update member's last_updated timestamp to mark successful scan
                    if member:
                        member.last_updated = datetime.datetime.now(timezone.utc)
                    
                except Exception as e:
                    logger.error(f"Error inserting snapshot for {u_clean}: {e}")
                    db_session.rollback()
                    continue
        
        db_session.commit()
        print(f"Done. Saved {count_snaps} snapshots and {count_bosses} boss records.")

    except asyncio.CancelledError:
        print("WOM harvest cancelled.")
        db_session.rollback()
        raise
    except Exception as e:
        print(f"Error during WOM Snapshot Processing: {e}")
        logger.exception("WOM Snapshot Error")
        db_session.rollback()
        raise
    finally:
        try:
            db_session.close()
            print("WOM database session closed")
        except Exception as e:
            logger.error(f"Error closing WOM session: {e}")



    # --- IDENTITY SYNC: Skipped to avoid database lock issues ---
    # Identity resolution now uses the same sqlite connection to avoid ORM locks.
    # Alias linkage is resolved inline when snapshots are saved.
    print("Identity resolution performed via sqlite alias lookup")

if __name__ == "__main__":
    asyncio.run(run_sqlite_harvest())
