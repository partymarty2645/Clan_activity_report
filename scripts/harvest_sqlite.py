import sys
import os
import asyncio
import json
import sqlite3
import datetime
from datetime import timezone
from typing import Optional

# Setup path
sys.path.append(os.getcwd())

from services.wom import wom_client, WOMClient
from services.discord import discord_service, DiscordFetcher
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

console = Console()

DB_PATH = "clan_data.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

async def fetch_member_data(username, wom=None):
    try:
        # Use injected WOM client or fall back to global singleton
        client = wom if wom is not None else wom_client
        # Get details (includes latest snapshot)
        p = await client.get_player_details(username)
        return (username, p)
    except Exception as e:
        # print(f"Error fetching {username}: {e}")
        return (username, None)

async def fetch_and_check_staleness(username, wom=None):
    # Wrapper to fetch details, check staleness, and optionally update
    try:
        # Use injected WOM client or fall back to global singleton
        client = wom if wom is not None else wom_client
        p = await client.get_player_details(username)
        if not p: return (username, None)
        
        # Check staleness
        updated_at_str = p.get('updatedAt')
        if updated_at_str:
            last_update = datetime.datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            now = datetime.datetime.now(timezone.utc)
            if (now - last_update).total_seconds() > 86400: # 24h
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
    # Use injected clients or fall back to factory/globals
    wom = wom_client_inject if wom_client_inject is not None else wom_client
    discord = discord_service_inject if discord_service_inject is not None else discord_service
    
    print(f"Connecting to {DB_PATH} via sqlite3...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # 0. Harvest Discord Messages (Async)
    # We run this first or in parallel? It uses its own DB session (ORM)
    try:
        print("Starting Discord Message Harvest...")
        # INCREMENTAL HARVEST: Get latest message date from DB to avoid re-fetching history
        try:
             cursor.execute(Queries.GET_LAST_MSG_DATE)
             last_msg_row = cursor.fetchone()
             last_msg_ts = last_msg_row[0] if last_msg_row else None
             
             founding_date = datetime.datetime(2025, 2, 14, tzinfo=timezone.utc)
             
             if last_msg_ts:
                 # Clean string and convert to DT
                 # Format usually "YYYY-MM-DD HH:MM:SS..." or ISO
                 # Sqlite often stores as string.
                 if isinstance(last_msg_ts, str):
                     last_msg_ts = last_msg_ts.replace(' ', 'T')
                     # Simple ISO parse
                     try:
                         # Append Z if missing for UTC assumption
                         if '+' not in last_msg_ts and 'Z' not in last_msg_ts:
                             last_msg_ts += '+00:00'
                         
                         start_date = datetime.datetime.fromisoformat(last_msg_ts)
                         # Ensure UTC
                         start_date = TimestampHelper.to_utc(start_date)
                         # Add 1ms to avoid fetching same last message
                         start_date += datetime.timedelta(milliseconds=1)
                         
                         print(f"  - Found previous messages. Resuming from {TimestampHelper.format_for_display(start_date)}...")
                     except:
                         start_date = founding_date
                 else:
                     start_date = founding_date
             else:
                 print("  - No previous messages found. fetching from Clan Founding (Feb 14, 2025)...")
                 start_date = founding_date

        except Exception as e:
            print(f"  - Error checking last message: {e}. Defaulting to Founding Date.")
            start_date = datetime.datetime(2025, 2, 14, tzinfo=timezone.utc)
            
        await discord.fetch(start_date=start_date)
        # print("  [DEBUG] Discord Fetch temporarily disabled for optimization test.")
    except Exception as e:
        print(f"Discord Harvest Failed: {e}")
    
    # 1. Get Members
    print("Fetching Group Members from WOM...")
    members = await wom.get_group_members(Config.WOM_GROUP_ID)
    print(f"Found {len(members)} members.")
    
    # Limit for testing if needed
    # members = members[:10] 
    
    # --- MEMBER SYNC (Source of Truth) ---
    print(f"Syncing {len(members)} members to 'clan_members' table...")
    active_usernames = []
    rows_to_upsert = []
    
    ts_now = TimestampHelper.now_utc()

    for m in members:
        # WOM API returns keys like 'username', 'role', 'joinedAt'
        raw_name = m.get('username', '')
        if not raw_name: continue
        
        u_clean = UsernameNormalizer.normalize(raw_name)
        active_usernames.append(u_clean)
        
        role = m.get('role', 'member')
        joined_at_str = m.get('joinedAt')
        
        joined_dt = None
        if joined_at_str:
            try:
                # Handle ISO format. API usually gives "2023-01-01T12:00:00.000Z"
                joined_dt = datetime.datetime.fromisoformat(joined_at_str.replace('Z', '+00:00'))
                # Ensure UTC
                joined_dt = TimestampHelper.to_utc(joined_dt)
            except Exception as e:
                 print(f"Warning: Could not parse joinedAt '{joined_at_str}' for {raw_name}: {e}")
                 # Fallback? If we fallback to now, key stats might be wrong (Days in clan = 0).
                 # Better to leave as None or try standard format?
                 pass
        
        # If joined_dt is None, and they are in the API, it means WOM doesn't know when they joined.
        # We can default to "Now" ONLY if it's a new insert? 
        # But for upsert, we might overwrite a valid old date with "Now" if the API returns null?
        # WOM usually returns joinedAt.
        # Let's ensure we don't accidentally overwrite existing valid data with None if possible?
        # Actually our upsert replaces everything.
        # If WOM API has it as null, then it IS null.
        # But let's log it.
        
        rows_to_upsert.append((u_clean, role, joined_dt, ts_now))

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
                
                if delete_ratio > 0.20:
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
        
    tasks = []
    ts_now = datetime.datetime.now(timezone.utc)
    
    skipped_count = 0
    for m in members:
        uname = m['username']
        
        # --- PHASE 5: LOCAL-FIRST OPTIMIZATION ---
        try:
            cursor.execute(Queries.CHECK_TODAY_SNAPSHOT, (uname,))
            if cursor.fetchone():
                # Already have data for today
                # Log only in verbose/trace mode or summary
                skipped_count += 1
                continue
        except Exception as query_err:
            logger.warning(f"Failed to check existing snapshot for {uname}: {query_err}")
            
        # If not skipped, add to queue (pass injected wom client)
        tasks.append(fetch_and_check_staleness(uname, wom=wom))

    if skipped_count > 0:
        print(f"  [Optimization] Skipped {skipped_count} players (Today's data already exists).")

    # tasks = [fetch_member_data(m['username']) for m in members]
    
    results = []
    # Determine if we are running in an interactive terminal
    # is_interactive = sys.stdout.isatty() and not os.environ.get("NO_RICH")
    is_interactive = False
    
    try:
        if is_interactive:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task_id = progress.add_task("[cyan]Fetching Snapshots...", total=len(tasks))
                
                for f in asyncio.as_completed(tasks):
                    res = await f
                    results.append(res)
                    progress.advance(task_id)
        else:
            # Non-interactive mode (e.g. piped to main.py) - Use simple logging to avoid buffering issues
            print(f"Fetching {len(tasks)} snapshots in batches...")
            completed_count = 0
            for f in asyncio.as_completed(tasks):
                res = await f
                results.append(res)
                completed_count += 1
                if completed_count % 5 == 0 or completed_count == len(tasks):
                    print(f"  Fetched {completed_count}/{len(tasks)} snapshots...")
                    sys.stdout.flush() # Force flush to ensure main.py sees it immediately
                
        print("Saving to Database...")
        
        # Prepare data for bulk insert
        snapshot_inserts = [] 
        
        count_snaps = 0
        count_bosses = 0
        
        ts_now = datetime.datetime.now(timezone.utc)
        
        # Open ORM session for member resolution
        from database.connector import SessionLocal
        db = SessionLocal()
        
        try:
            for username, data in results:
                if not data: continue
                
                u_clean = UsernameNormalizer.normalize(username)
                snap = data.get('latestSnapshot')
                if not snap: continue
                
                # Parse
                snap_data = snap.get('data', {})
                skills = snap_data.get('skills', {})
                bosses = snap_data.get('bosses', {})
                
                xp = skills.get('overall', {}).get('experience', 0)
                ehp = data.get('ehp', 0)
                ehb = data.get('ehb', 0)
                
                total_boss = sum(b.get('kills', 0) for b in bosses.values() if b.get('kills', 0) > 0)
                
                raw_json = json.dumps(data)
                
                # Resolve member_id via alias lookup
                member_id = resolve_member_by_name(db, u_clean)
                if not member_id:
                    logger.warning(f"Could not resolve member_id for snapshot username '{u_clean}'. Snapshot will be saved with user_id=NULL.")
                
                try:
                    # 1. Insert Snapshot with resolved member_id
                    cursor.execute(Queries.INSERT_SNAPSHOT, (u_clean, ts_now, xp, total_boss, ehp, ehb, raw_json, member_id))
                    
                    snap_id = cursor.lastrowid
                    count_snaps += 1
                    
                    # 2. Insert Bosses
                    boss_rows = []
                    for b_name, b_val in bosses.items():
                        kills = b_val.get('kills', -1)
                        rank = b_val.get('rank', -1)
                        if kills > -1:
                            boss_rows.append((snap_id, b_name, kills, rank))
                    
                    if boss_rows:
                        cursor.executemany(Queries.INSERT_BOSS_SNAPSHOT, boss_rows)
                        count_bosses += len(boss_rows)
                        
                except Exception as e:
                    # UNIQUE constraint might trigger here
                    if "UNIQUE constraint failed" in str(e):
                        # print(f"Skipping duplicate snapshot for {u_clean}")
                        pass
                    else:
                        print(f"Error saving {u_clean}: {e}")

            conn.commit()
            print(f"Done. Saved {count_snaps} snapshots and {count_bosses} boss records.")
            
        finally:
            db.close()

    finally:
        print("DEBUG: Closing WOM Client...")
        await wom.close()
        print("DEBUG: Closing DB Connection...")
        conn.close()

if __name__ == "__main__":
    asyncio.run(run_sqlite_harvest())
