import asyncio
from collections import Counter, defaultdict
import os
import sqlite3
import csv
import shutil
import logging
from pathlib import Path
import pandas as pd
import re
from tqdm.asyncio import tqdm
import database 
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from wom import wom_client
from bot import run_discord_fetch

# Load environment variables
load_dotenv(override=True)

# --- Configuration ---
WOM_GROUP_ID = os.getenv('WOM_GROUP_ID')
OUTPUT_FILE_CSV = 'clan_report_summary_merged.csv'
OUTPUT_FILE_XLSX = 'clan_report_summary_merged.xlsx'
ARCHIVE_DIR = 'archive'
BACKUP_DIR = 'backups'

# --- Test Configuration ---
TEST_MODE = os.getenv('WOM_TEST_MODE', 'False').lower() == 'true'
TEST_PLAYER_LIMIT = int(os.getenv('WOM_TEST_LIMIT', 5))  # Default to 5 for quick checks

# --- Excel Formatting Configuration ---
EXCEL_ZERO_HIGHLIGHT = os.getenv('EXCEL_ZERO_HIGHLIGHT', 'true').lower() == 'true'
EXCEL_ZERO_BG_COLOR = os.getenv('EXCEL_ZERO_BG_COLOR', '#FFC7CE')  # Light red
EXCEL_ZERO_FONT_COLOR = os.getenv('EXCEL_ZERO_FONT_COLOR', '#9C0006')  # Dark red
EXCEL_COLUMN_WIDTH = int(os.getenv('EXCEL_COLUMN_WIDTH', 12))
EXCEL_USERNAME_WIDTH = int(os.getenv('EXCEL_USERNAME_WIDTH', 20))

# Date Ranges (From Env)
def get_custom_dates():
    start_str = os.getenv('CUSTOM_START_DATE', '2025-02-14')
    # End date is always NOW (Dynamic) as per user request
    # end_str = os.getenv('CUSTOM_END_DATE', '2025-12-08') 
    try:
        s = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        e = datetime.now(timezone.utc)
        return s, e
    except:
        # Fallback
        return datetime(2025, 2, 14, tzinfo=timezone.utc), datetime.now(timezone.utc)

CUSTOM_START, CUSTOM_END = get_custom_dates()

# Regex for Bridge Bot (if used)
REGEX_BRIDGE = r"\*\*(.+?)\*\*:"

# Ranking Weights
ROLE_WEIGHTS = {
    'owner': 100,
    'deputy_owner': 90,
    'dragonstone': 80,
    'zenyte': 80,
    'administrator': 70,
    'saviour': 60,
    # All others (Member, Admin, etc) default to 20
    'prospector': 10,
    'guest': 0
}

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging initialized.")
    logging.info(f"Version: 2.0 (Upgraded)")
    logging.info(f"Configuration: Group={WOM_GROUP_ID}, TestMode={TEST_MODE}")

def backup_database():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    if os.path.exists(database.DB_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dst = os.path.join(BACKUP_DIR, f"clan_data_{timestamp}.db")
        shutil.copy2(database.DB_FILE, dst)
        logging.info(f"Database backup created: {dst}")

    # Cleanup: Keep only 5 newest files
    try:
        files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if os.path.isfile(os.path.join(BACKUP_DIR, f))]
        files.sort(key=os.path.getmtime, reverse=True) # Newest first
        
        if len(files) > 5:
            for f in files[5:]:
                try:
                    os.remove(f)
                    logging.info(f"Deleted old backup: {f}")
                except Exception as e:
                    logging.warning(f"Failed to delete old backup {f}: {e}")
    except Exception as e:
        logging.warning(f"Error during backup cleanup: {e}")

def archive_last_report():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        
    for f in [OUTPUT_FILE_CSV, OUTPUT_FILE_XLSX]:
        if os.path.exists(f):
            timestamp = datetime.now().fromtimestamp(os.path.getmtime(f)).strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(f)
            dst = os.path.join(ARCHIVE_DIR, f"{name}_{timestamp}{ext}")
            shutil.copy2(f, dst)
            logging.info(f"Archived old report: {dst}")

    # Cleanup: Keep only 10 newest files (approx 5 sets of reports)
    try:
        files = [os.path.join(ARCHIVE_DIR, f) for f in os.listdir(ARCHIVE_DIR) if os.path.isfile(os.path.join(ARCHIVE_DIR, f))]
        files.sort(key=os.path.getmtime, reverse=True) # Newest first
        
        if len(files) > 10:
            for f in files[10:]:
                try:
                    os.remove(f)
                    logging.info(f"Deleted old archive: {f}")
                except Exception as e:
                    logging.warning(f"Failed to delete old archive {f}: {e}")
    except Exception as e:
        logging.warning(f"Error during archive cleanup: {e}")

def clean_int(val):
    try:
        return int(val)
    except:
        return 0

async def update_discord_db():
    """
    Syncs Discord messages into the SQLite database.
    Handles both forward sync (new messages) and backfill (gap filling).
    """
    logging.info("--- Syncing Discord Messages (Database) ---")
    
    # 1. Init DB
    database.init_db()
    
    # 2. Analyze DB State
    latest_ts = database.get_latest_message_time()
    earliest_ts = database.get_earliest_message_time()
    
    # Ensure UTC awareness for comparison
    start_backfill_target = CUSTOM_START
    
    # --- A. Backfill (Gap Filling) ---
    if earliest_ts:
        if earliest_ts.endswith('Z'): earliest_ts = earliest_ts[:-1] + '+00:00'
        earliest_dt = datetime.fromisoformat(earliest_ts)
        
        # If DB starts AFTER our target start date (with some buffer), we have a gap
        if earliest_dt > start_backfill_target + timedelta(days=1):
            logging.info(f"  [Backfill] Gap detected! DB starts at {earliest_dt}, need data from {start_backfill_target}")
            logging.info(f"  Fetching missing history: {start_backfill_target} -> {earliest_dt}")
            # Fetch older messages (reverse chronological usually, but our bot handles ranges)
            gap_msgs = await run_discord_fetch(start_date=start_backfill_target, end_date=earliest_dt)
            if gap_msgs:
                count, skipped = database.insert_messages(gap_msgs)
                logging.info(f"  [Backfill] Inserted {count} older messages (Skipped {skipped} duplicates).")
            else:
                logging.info("  [Backfill] No messages found in gap.")
        else:
            logging.info(f"  [Backfill] History looks complete (Starts: {earliest_dt}).")
    else:
        logging.info("  Database empty. Initializing full fetch...")
    
    # --- B. Forward Sync (New Messages) ---
    start_fetch_date = None
    if latest_ts:
        if latest_ts.endswith('Z'): latest_ts = latest_ts[:-1] + '+00:00'
        start_fetch_date = datetime.fromisoformat(latest_ts)
        logging.info(f"  [Forward] Last DB message: {start_fetch_date}")
    else:
        # If empty, start from CUSTOM_START
        start_fetch_date = start_backfill_target
        logging.info(f"  [Forward] Starting fresh fetch from: {start_fetch_date}")

    logging.info(f"  [Forward] Fetching new messages since {start_fetch_date}...")
    new_msgs = await run_discord_fetch(start_date=start_fetch_date, end_date=None)
    
    if new_msgs:
        # TQDM for insertion (since fetching is done in bot)
        logging.info("  Inserting messages into DB...")
        count = 0
        skipped = 0
        
        # Simple count display for now as insert_messages is bulk
        count, skipped = database.insert_messages(new_msgs)
        logging.info(f"  [Forward] Inserted {count} new messages (Skipped {skipped} duplicates).")
    else:
        logging.info("  [Forward] No new messages found.")

def clean_int(val):
    try:
        return int(val)
    except:
        return 0

def safe_save(df, filename, method='csv', **kwargs):
    """
    Attempts to save a dataframe. If PermissionError (file open), 
    saves to a new filename with timestamp appended.
    """
    try:
        if method == 'csv':
            df.to_csv(filename, **kwargs)
        logging.info(f"Saved {method.upper()}: {filename}")
        return filename
    except PermissionError:
        base, ext = os.path.splitext(filename)
        new_name = f"{base}_{int(datetime.now().timestamp())}{ext}"
        logging.warning(f"  [WARN] Could not save to '{filename}' (File open?). Saving to '{new_name}' instead.")
        
        if method == 'csv':
            df.to_csv(new_name, **kwargs)
        return new_name
    except Exception as e:
        logging.error(f"Failed to save {filename}: {e}")
        return None

def normalize_user_string(s):
    """
    Normalizes a username for comparison by:
    1. Lowercasing
    2. Replacing underscores and hyphens with spaces
    3. Stripping whitespace
    This ensures 'Luke_Jon', 'l-loi', and 'Luke Jon' all match.
    """
    if not s: return ""
    return s.lower().replace('_', ' ').replace('-', ' ').strip()

def count_messages_in_db_range(start_dt, end_dt, target_usernames):
    """
    Queries DB for messages in range and counts them for target users.
    Uses smart normalization to match 'Luke_Jon' (Discord) with 'luke jon' (WOM).
    """
    # Create valid keys for results (original lowercased keys)
    # But map NORMALIZED keys to them.
    # e.g. normalize('Luke_Jon') -> 'luke jon'
    # we want lookup['luke jon'] -> 'luke jon' (the real key in our results dict)
    
    lookup_map = {}
    for u in target_usernames:
        # key in 'results' is u.lower()
        res_key = u.lower()
        norm = normalize_user_string(u)
        lookup_map[norm] = res_key
        
    counts = {u.lower(): 0 for u in target_usernames}
    regex = re.compile(REGEX_BRIDGE)
    
    # Ensure start/end are UTC
    if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=timezone.utc)
    
    # Get messages from DB (Generator or List)
    messages = database.get_messages_in_range(start_dt, end_dt)
    
    for msg in messages:
        content = msg['content'] or ''
        raw_author = msg['author_name'] or ''
        
        # 1. Direct Author Check
        norm_author = normalize_user_string(raw_author)
        if norm_author in lookup_map:
            real_key = lookup_map[norm_author]
            counts[real_key] += 1
        
        # 2. Bridge Bot Check
        matches = regex.findall(content)
        for m in matches:
            norm_m = normalize_user_string(m)
            if norm_m in lookup_map:
                real_key = lookup_map[norm_m]
                counts[real_key] += 1
                
    return counts

async def fetch_api_gains_fallback(group_id, start_dt, end_dt, usernames):
    """
    Fetches gains for specific users when local history is missing.
    Uses /players/{username}/gained to get ALL data (XP, EHP, EHB, Boss Kills).
    """
    logging.info(f"   [Fallback] Fetching API gains for {len(usernames)} users individually (parallel)...")
    
    results_map = {u: {} for u in usernames}
    
    async def fetch_one_user_gains(username):
        """Fetch gains for a single user."""
        try:
            params = {
                'startDate': start_dt.isoformat(),
                'endDate': end_dt.isoformat()
            }
            # Use semaphore from wom_client for concurrency control
            async with wom_client._semaphore:
                data = await wom_client._request(
                    'GET', 
                    f'/players/{username}/gained', 
                    params=params
                )
            
            d = data.get('data', {})
            
            # Extract Metrics
            xp = d.get('skills', {}).get('overall', {}).get('experience', {}).get('gained', 0)
            ehp = d.get('computed', {}).get('ehp', {}).get('value', {}).get('gained', 0)
            ehb = d.get('computed', {}).get('ehb', {}).get('value', {}).get('gained', 0)
            
            # Sum Boss Kills
            boss_kills = 0
            if 'bosses' in d:
                for b_val in d['bosses'].values():
                    boss_kills += b_val.get('kills', {}).get('gained', 0)
            
            # Store
            return username, {
                'overall': xp,
                'ehp': ehp,
                'ehb': ehb,
                'boss_kills': boss_kills
            }
        except Exception as e:
            logging.warning(f"     [Fallback] Failed to fetch {username}: {e}")
            return username, {'overall': 0, 'ehp': 0, 'ehb': 0, 'boss_kills': 0}
    
    # Parallel fetch with progress bar
    tasks = [fetch_one_user_gains(u) for u in usernames]
    for task in tqdm.as_completed(tasks, total=len(tasks), desc="Fetching Fallback Gains (Parallel)"):
        username, data = await task
        results_map[username] = data
    
    return results_map
            
    return results_map
        
    return results_map

async def process_wom_data(group_id, members_list):
    """
    1. Fetches full player details (Snapshot) for all members.
    2. Saves snapshots to DB.
    3. Returns a dictionary with current stats including EHP/EHB.
    """
    logging.info(f"Processing WOM data for {len(members_list)} members (Snapshots)...")
    
    usernames = [m['username'] for m in members_list]
    
    # Pre-check: count how many we already have for today
    existing_today = 0
    # simple check to see if we should warn/log
    # (Optional optimization: get all today's users in one query, but valid to check inside loop for simplicity)

    # DEBUG: Check for luke_jon
    for u in usernames:
        if 'luke' in u.lower():
            logging.info(f"  [DEBUG] Found member: '{u}' (encoded: {u.encode('utf-8')})")
    
    current_snapshots = {} # username -> {stats}
    
    # Parallel Fetch with semaphore (controlled by WOMClient.max_concurrent)
    async def fetch_one_player(username):
        u_clean = username.lower()
        
        # 1. Check Cache (Database)
        # start_cache = datetime.now()
        cached = database.get_todays_snapshot(u_clean)
        if cached:
            # cached is (total_xp, total_boss_kills, ehp, ehb, raw_data)
            # We can skip API fetch!
            logging.info(f"  [Cache] Using existing snapshot for {username}") 
            return (u_clean, {
                'total_boss_kills': cached[1],
                'ehp': cached[2],
                'ehb': cached[3],
                'xp': cached[0]
            })

        # 2. Fetch from API
        try:
            p = await wom_client.get_player_details(username)
            
            # Parse Data
            u_clean = p['username'].lower()
            
            try:
                snap = p.get('latestSnapshot') or {}
                data_block = snap.get('data') or {}
                
                # Boss Kills Sum
                bosses = data_block.get('bosses') or {}
                total_boss_kills = 0
                for b_key, b_val in bosses.items():
                    kills = b_val.get('kills', 0)
                    if kills > 0:
                        total_boss_kills += kills
                
                ehp = p.get('ehp', 0)
                ehb = p.get('ehb', 0)
                
                # Save to DB
                skills = data_block.get('skills') or {}
                total_xp = skills.get('overall', {}).get('experience', 0)
                raw_json = "" 
                database.insert_wom_snapshot_full((u_clean, total_xp, total_boss_kills, ehp, ehb, raw_json))
                
                return (u_clean, {
                    'total_boss_kills': total_boss_kills,
                    'ehp': ehp,
                    'ehb': ehb,
                    'xp': total_xp
                })
                
            except Exception as parse_e:
                logging.error(f"Error parsing profile for {u_clean}: {parse_e}")
                return (username.lower(), None)
                
        except Exception as e:
            return (username.lower(), None)
    
    # Create tasks for parallel execution
    tasks = [fetch_one_player(u) for u in usernames]
    
    # Execute with progress bar
    results = []
    
    for coro in tqdm.as_completed(tasks, desc="Fetching/Loading Profiles", total=len(tasks)):
        result = await coro
        results.append(result)
    
    # Build snapshot map
    for u_clean, stats in results:
        if stats:
            current_snapshots[u_clean] = stats

    return current_snapshots

async def main():
    setup_logging()
    
    # --- 1. Startup & Safety ---
    logging.info("--- Starting Clan Report Script ---")
    backup_database()
    archive_last_report()

    if not WOM_GROUP_ID:
        logging.error("Error: WOM_GROUP_ID not set.")
        return

    # --- 2. Trigger Group Update ---
    # We still trigger update to ensure WOM has fresh data, even if we pull details later
    WOM_GROUP_SECRET = os.getenv('WOM_GROUP_SECRET', '728834546')
    logging.info(f"--- Triggering WOM Group Update (ID: {WOM_GROUP_ID}) ---")
    try:
        resp = await wom_client.update_group(WOM_GROUP_ID, WOM_GROUP_SECRET)
        logging.info(f"  Update triggered: {resp.get('message', 'Success')}")
        logging.info("  Waiting 5 minutes for update to propagate... (Press ESC to skip)")
        if not TEST_MODE:
            # Interactive Wait Loop
            import msvcrt
            import time
            import sys
            
            start_wait = time.time()
            skipped = False
            # Simple progress bar manually
            try:
                while (time.time() - start_wait) < 300: # 300s = 5m
                    # Check for keypress
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if ord(key) == 27: # ESC
                            print("\n  [User requested Skip]")
                            skipped = True
                            break
                    
                    # Print progress
                    elapsed = int(time.time() - start_wait)
                    sys.stdout.write(f"\r  Waiting... {elapsed}/300s (Press ESC to skip)")
                    sys.stdout.flush()
                    
                    await asyncio.sleep(0.1)
            except ImportError:
                # Fallback for non-windows if msvcrt missing, though user says Windows
                await asyncio.sleep(300)

            if not skipped:
                print("\n  Wait complete.")
        else:
             logging.info("  [Test Mode] Skipping wait.")
    except Exception as e:
        logging.error(f"  Error updating group (proceeding anyway): {e}")

    # --- 3. Get WOM Member List (fast) ---
    logging.info("--- Fetching WOM Group Members ---")
    members_data = await wom_client.get_group_members(WOM_GROUP_ID)
    
    # DEBUG TRACES REMOVED
    # Re-evaluate logic to ensure it catches the env var
    IS_TEST_RUN = os.getenv('WOM_TEST_MODE', 'False').lower() == 'true'
    
    
    if IS_TEST_RUN:
        logging.info(f"  [TEST MODE] Limiting to first {TEST_PLAYER_LIMIT} members.")
        members_data = members_data[:TEST_PLAYER_LIMIT]

    # --- 4. Name Change Detection (The "Missing Person" Heuristic) ---
    logging.info("--- Checking for Name Changes ---")
    
    # Get users who were here last run but are gone now
    last_run_users = set(database.get_last_active_users())
    current_map = {m['username'].lower(): m['username'] for m in members_data}
    last_run_map = {u.lower(): u for u in last_run_users}
    
    missing_lower = set(last_run_map.keys()) - set(current_map.keys())
    
    if missing_lower and last_run_users: # Only run if we actually have history
        logging.info(f"  Found {len(missing_lower)} users missing since last run. Analysing...")
        
        for missing_l in missing_lower:
            original_name = last_run_map[missing_l]
            
            # Don't check everyone, only check if we suspect a rename (simple heuristic: specific API call)
            try:
                # Search specifically for this old name
                # We trust WOM to tell us if "IronMan" changed to "FeMan"
                changes = await wom_client.search_name_changes(original_name, limit=5)
                
                target_change = None
                for c in changes:
                    # Strict Match: The API search is fuzzy, so we must confirm oldName matches exactly (case-insensitive)
                    if c.get('oldName', '').lower() == missing_l:
                         target_change = c
                         break
                
                if target_change:
                    new_name = target_change.get('newName')
                    logging.info(f"  [Name Change DETECTED] '{original_name}' -> '{new_name}'")
                    
                    # CRITICAL SAFETY CHECK: Collision Detection
                    if new_name.lower() in last_run_map:
                         # Danger: 'new_name' existed yesterday. 'old_name' existed yesterday.
                         # Now 'old_name' is 'new_name'. This implies a merge or swap. STOP.
                         logging.warning(f"  ⚠️  CRITICAL: Name collision detected. '{new_name}' already existed in last run. " 
                                       f"Cannot auto-migrate '{original_name}' to '{new_name}'. Manual intervention required.")
                         continue
                         
                    # Safe to update
                    success = database.update_username(original_name, new_name)
                    if success:
                        logging.info(f"  ✅ SUCCESS: Database migrated from '{original_name}' to '{new_name}'. History preserved.")
                else:
                    logging.info(f"  User '{original_name}' left the clan (no name change found).")
                    
            except Exception as e:
                logging.error(f"  Error checking name change for {original_name}: {e}")
    else:
        logging.info("  No missing users detected (or first run).")
    
    # --- 5. Parallel Discord Sync & WOM Player Snapshots ---
    logging.info("--- Starting Parallel Operations (Discord + WOM Snapshots) ---")
    
    # Run Discord sync and WOM player snapshot fetching in parallel
    discord_task = asyncio.create_task(update_discord_db())
    wom_snapshots_task = asyncio.create_task(process_wom_data(WOM_GROUP_ID, members_data))
    
    # Wait for both to complete
    await discord_task
    current_stats_map = await wom_snapshots_task
    
    logging.info("--- Parallel Operations Complete ---")

    # --- 6. Define Periods ---
    now = datetime.now(timezone.utc)
    
    periods = {
        '7d': {
            'start': now - timedelta(days=7),
            'end': now,
            'xp_key': 'XP Gained 7d',
            'msg_key': 'Messages 7d',
            'boss_key': 'Boss kills 7d'
        },
        '30d': {
            'start': now - timedelta(days=30),
            'end': now,
            'xp_key': 'XP Gained 30d',
            'msg_key': 'Messages 30d',
            'boss_key': 'Boss kills 30d'
        },
        '70d': {
            'start': now - timedelta(days=70),
            'end': now,
            'xp_key': 'XP Gained 70d',
            'msg_key': 'Messages 70d',
            'boss_key': 'Boss kills 70d'
        },
        '150d': {
            'start': now - timedelta(days=150),
            'end': now,
            'xp_key': 'XP Gained 150d',
            'msg_key': 'Messages 150d',
            'boss_key': 'Boss kills 150d'
        },
        'total': {
            'start': CUSTOM_START,
            'end': CUSTOM_END,
            'xp_key': 'Total xp gained',
            'msg_key': 'Total Messages',
            'boss_key': 'Total boss kills'
        }
    }
    
    member_usernames = [m['username'] for m in members_data]
    
    # Prepare Result Structure
    results = {}
    for m in members_data:
        u = m['username']
        role = m.get('role', 'member')
        rank_score = ROLE_WEIGHTS.get(role, 0)
        
        results[u.lower()] = {
            'Username': u,
            'Role': role,
            'Rank Score': rank_score
        }
        
        # Init all keys
        for p in periods.values():
            results[u.lower()][p['xp_key']] = 0
            results[u.lower()][p['msg_key']] = 0
            if p.get('boss_key'): results[u.lower()][p['boss_key']] = 0

    ordered_columns = [
        'Username', 'Role',
        'XP Gained 7d', 'XP Gained 30d', 'XP Gained 70d', 'XP Gained 150d', 'Total xp gained',
        'Messages 7d', 'Messages 30d', 'Messages 70d', 'Messages 150d', 'Total Messages',
        'Boss kills 7d', 'Boss kills 30d', 'Boss kills 70d', 'Boss kills 150d', 'Total boss kills'
    ]

    # --- 7. Calculate Gains & Message Counts ---
    logging.info("--- Processing Periods (Gains & Messages) ---")
    
    for pid, info in periods.items():
        logging.info(f"Processing '{pid}'...")
        
        # A. Discord Counts
        msg_counts = count_messages_in_db_range(info['start'], info['end'], member_usernames)
        
        # B. WOM Gains (Hybrid: Local Delta or API Fallback)
        # We need gains for ALL metrics if keys exist
        
        # Start with API Fallback for XP if needed (bulk fetch is efficient)
        # But we really want to try Local Delta first for each user.
        
        # We'll iterate users.
        api_fallback_needed = [] # list of usernames
        
        for u in member_usernames:
            u_lower = u.lower()
            curr = current_stats_map.get(u_lower)
            
            # Message Count
            if u_lower in msg_counts:
                results[u_lower][info['msg_key']] = msg_counts[u_lower]
                
            if not curr:
                continue # Can't calculate gains if we don't have current
            
            # Try to get Old Snapshot
            old_snap = database.get_snapshot_before(u_lower, info['start'])
            # Returns: (timestamp, total_xp, total_boss_kills, ehp, ehb, raw_data)
            
            if old_snap:
                # Calculate Delta
                # curr is dict: {xp, bosses, ehp, ehb}
                # old_snap is tuple: 0=ts, 1=xp, 2=boss, 3=ehp, 4=ehb
                
                g_xp = curr['xp'] - (old_snap[1] or 0)
                g_boss = curr['total_boss_kills'] - (old_snap[2] or 0)
                g_ehp = curr['ehp'] - (old_snap[3] or 0)
                g_ehb = curr['ehb'] - (old_snap[4] or 0)
                
                # Sanity check: Gains shouldn't be negative usually (unless de-leveled or bug). 
                # Keep negatives or clamp to 0? WOM allows negatives for losses.
                
                results[u_lower][info['xp_key']] = g_xp
                if info.get('ehp_key'): results[u_lower][info['ehp_key']] = float(f"{g_ehp:.2f}")
                if info.get('ehb_key'): results[u_lower][info['ehb_key']] = float(f"{g_ehb:.2f}")
                if info.get('boss_key'): results[u_lower][info['boss_key']] = g_boss
                
            else:
                # No snapshot -> Fallback to API
                api_fallback_needed.append(u_lower)

        # C. Run API Fallback for missing snapshots
        if api_fallback_needed:
            logging.info(f"  [Fallback] fetching API gains for {len(api_fallback_needed)} users in {pid}...")
            # We only fetch XP from API currently in our helper.
            # Upgrading fallback to fetch other metrics is complex via bulk endpoint. 
            # We'll stick to XP fallback for now as promised, others will be 0 until history builds.
            # Wait, user might want XP at least.
            
            fallback_gains = await fetch_api_gains_fallback(WOM_GROUP_ID, info['start'], info['end'], api_fallback_needed)
            
            for u_lower, metrics_data in fallback_gains.items():
                # metrics_data is { 'overall': ..., 'ehp': ..., 'ehb': ... }
                
                if 'overall' in metrics_data:
                    results[u_lower][info['xp_key']] = metrics_data['overall']
                    
                # Map 'ehp' -> ehp_key
                if 'ehp' in metrics_data and info.get('ehp_key'):
                    results[u_lower][info['ehp_key']] = metrics_data['ehp']
                    
                # Map 'ehb' -> ehb_key
                if 'ehb' in metrics_data and info.get('ehb_key'):
                    results[u_lower][info['ehb_key']] = metrics_data['ehb']
                    
                # Map 'boss_kills' -> boss_key
                if 'boss_kills' in metrics_data and info.get('boss_key'):
                    results[u_lower][info['boss_key']] = metrics_data['boss_kills']

    # --- 8. Reporting (Excel) ---
    logging.info("--- Generating Enhanced Reports ---")
    
    # --- TEXT ANALYSIS (Questions & Fav Word) ---
    logging.info("--- Analyzing Text Stats (Questions & Favorite Words) ---")
    
    # Define Stop Words (Common + Bot/Jargon + IDs)
    STOP_WORDS = {
        # Standard Grammar
        'the', 'a', 'an', 'and', 'but', 'or', 'if', 'because', 'as', 'what',
        'when', 'where', 'how', 'who', 'why', 'which', 'this', 'that', 'these', 'those',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'i', 'me', 'my', 'mine', 'you', 'your', 'yours', 'he', 'him', 'his', 'she', 'her', 'hers',
        'it', 'its', 'we', 'us', 'our', 'ours', 'they', 'them', 'their', 'theirs',
        'to', 'from', 'in', 'on', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'of',
        'again', 'further', 'then', 'once', 'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
        's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren',
        'could', 'didn', 'doesn', 'hadn', 'hasn', 'haven', 'isn', 'ma', 'might', 'must', 'need', 'shan', 'shouldn',
        'wasn', 'weren', 'won', 'wouldn', 'im', 'u', 'dont', 'cant', 'thats', 'didnt', 'whats', 'theres', 'got', 'get',
        'like', 'one', 'good', 'bad', 'well', 'going', 'know', 'think', 'see', 'say', 'look', 'make', 'go', 'come',
        'take', 'want', 'give', 'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call',
        
        # Bot & Game Jargon (Specific Exclusions)
        'bot', 'statsicon', 'combatachievementsicon',
        'ironman_chat_badge', 'group_ironman_chat_badge', 'bountyhuntertradericon', 'speedrunningshopicon',
        'gnome_child', 'http', 'https', 'www', 'com', 'scams',
        
        # Ranks (User Provided List + Common)
        'prospector', 'spellcaster', 'astral', 'wintumber', 'therapist', 'saviour', 'wrath', 
        'apothecary', 'dragonstone', 'tztok', 'slayer', 'owner', 'wild', 'doctor', 'runecrafter', 
        'bob', 'deputy_owner', 'deputy', 'hellcat', 'short_green_guy', 'artillery', 'smiter', 'zamorakian', 
        'gamer', 'prodigy', 'zenyte', 'dragon', 'administrator', 'member', 'guest', 'smile', 
        'recruited', 'role', 'rank', 'score', 'messages', 'gained', 'total', 'unknown',
        
        # User Manual Rejections (Names, Game Terms, etc.)
        'armadylean', 'sir', 'gowi', 'death', 'achiever', 'tzkal', 'imp', 'nachokitty69', 
        'skulled', 'feeder', 'jbwell', 'grandkingbot', 'baxy', 'docofmed', 'flooggeer',
        
        # Numbers/IDs
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '000'
    }

    # Massive Game Ranks & Terms Blacklist (User Provided)
    GAME_RANKS_AND_TERMS = {
        # Army Ranks
        'dogsbody', 'minion', 'recruit', 'pawn', 'private', 'corporal', 'novice', 'sergeant', 'cadet',
        'page', 'noble', 'adept', 'legionnaire', 'lieutenant', 'proselyte', 'captain', 'major', 'general', 'master',
        'officer', 'commander', 'colonel', 'brigadier', 'admiral', 'marshal',
        # Gemstones
        'opal', 'jade', 'red', 'topaz', 'sapphire', 'emerald', 'ruby', 'diamond', 'onyx',
        # Non-human
        'kitten', 'wily', 'beast', 'gnome', 'child', 'elder', 'short', 'green', 'guy',
        # Regions
        'misthalinian', 'karamjan', 'asgarnian', 'kharidian', 'morytanian', 'kandarin', 'fremennik', 'tirannian',
        # Religions
        'brassican', 'saradominist', 'guthixian', 'serenist', 'bandosian', 'zarosian', 'xerician',
        # Rune symbols
        'air', 'mind', 'water', 'earth', 'fire', 'body', 'cosmic', 'chaos', 'nature', 'law', 'blood', 'soul',
        # Trees
        'diseased', 'pine', 'oak', 'willow', 'maple', 'yew', 'blisterwood', 'magic',
        # Skills & Roles
        'attacker', 'enforcer', 'defender', 'ranger', 'priest', 'magician', 'medic', 'athlete', 'herbologist',
        'thief', 'crafter', 'fletcher', 'miner', 'smith', 'fisher', 'cook', 'firemaker', 'lumberjack',
        'farmer', 'constructor', 'hunter', 'skiller', 'competitor',
        # Capes
        'holy', 'unholy', 'natural', 'sage', 'destroyer', 'mediator', 'legend', 'myth', 'maxed',
        # Skilling-focused
        'anchor', 'merchant', 'harpoon', 'carry',
        # Combat-focused
        'archer', 'battlemage', 'infantry', 'looter', 'sniper', 'crusader',
        # Misc
        'mentor', 'prefect', 'leader', 'supervisor', 'superior', 'executive', 'senator', 'monarch',
        'scavenger', 'labourer', 'worker', 'forager', 'hoarder', 'gatherer', 'collector',
        'bronze', 'iron', 'steel', 'gold', 'mithril', 'adamant', 'rune',
        'protector', 'bulwark', 'justiciar', 'sentry', 'guardian', 'warden', 'vanguard', 'templar',
        'squire', 'duellist', 'striker', 'ninja', 'inquisitor', 'expert', 'knight', 'paladin',
        'goon', 'brawler', 'bruiser', 'scourge', 'fighter', 'warrior', 'barbarian', 'berserker',
        'staff', 'crew', 'helper', 'sheriff', 'grey', 'pink', 'purple', 'blue', 'orange', 'yellow',
        'wizard', 'trickster', 'illusionist', 'summoner', 'necromancer', 'warlock', 'witch', 'seer',
        'assassin', 'cutpurse', 'bandit', 'scout', 'burglar', 'rogue', 'smuggler', 'brigand',
        'oracle', 'pure', 'champion', 'epic', 'mystic', 'hero', 'trialist', 'defiler',
        'scholar', 'councillor', 'recruiter', 'learner', 'scribe', 'assistant', 'teacher', 'coordinator',
        'walker', 'wanderer', 'pilgrim', 'vagrant', 'racer', 'strider',
        'druid', 'healer', 'zealot', 'cleric', 'shaman',
        'adventurer', 'explorer', 'quester', 'raider', 'completionist', 'elite',
        'firestarter', 'specialist', 'pyromancer', 'ignitor', 'artisan', 'legacy',
        
        # Specific Badges/Variables reported
        'unranked_group_ironman_chat_badge', 'hardcore_ironman_chat_badge'
    }
    
    STOP_WORDS.update(GAME_RANKS_AND_TERMS)

    # "Auto-Announcement" keywords - if message contains these, skip it entirely (it's not user chat)
    # These often appear in "User has achieved..." or "User received a drop..." messages
    AUTO_ANNOUNCEMENT_TRIGGERS = [
        'received', 'completed', 'reached', 'log', 'collection', 'loot', 'burnt', 'level', 
        'maxed', 'coins', 'xp', 'kill', 'kills', 'kc', 'combat', 'achievements', 'valuable drop', 'achieved'
    ]
    
    # Whitelist to protect slang even if they end up in stop lists somehow (safety)
    ALLOWED_SLANG = {'lol', 'gz', 'lmao', 'ty', 'haha', 'yeah', 'gzz', 'gzzz', 'tyvm'}
    
    # Data structs
    user_q_counts = defaultdict(int)        # username -> question_count
    user_word_counts = defaultdict(Counter) # username -> Counter(words)
    
    # 1. Normalize "Target" usernames map for fast lookup
    target_users_map = {}
    for u in member_usernames:
        target_users_map[normalize_user_string(u)] = u.lower()
        
    # --- DYNAMIC STOP LIST: Block ALL Discord Usernames & OSRS Names ---
    # This prevents "partymarty94" or "gowi" from being the favorite word
    try:
        conn = sqlite3.connect(database.DB_FILE) 
        cursor = conn.cursor()
        
        # 1. Discord Author Names
        cursor.execute("SELECT DISTINCT author_name FROM discord_messages")
        discord_names = [r[0] for r in cursor.fetchall() if r[0]]
        
        # 2. WOM/OSRS Usernames (Snapshots)
        cursor.execute("SELECT DISTINCT username FROM wom_snapshots")
        osrs_names = [r[0] for r in cursor.fetchall() if r[0]]
        
        conn.close()
        
        all_names = set(discord_names + osrs_names)
        logging.info(f"Loaded {len(all_names)} unique usernames to block from analysis.")
        
        for name in all_names:
            norm = name.lower()
            # Block full name
            STOP_WORDS.add(norm)
            # Block parts (e.g. "sir", "gowi" OR "berzerker_rs" -> "berzerker", "rs")
            # SPLIT ON UNDERSCORE TOO: [\W_] means non-word chars OR underscore
            parts = re.split(r'[\W_]', norm)
            for p in parts:
                if len(p) > 2: 
                    STOP_WORDS.add(p)
                    
    except Exception as e:
        logging.error(f"Failed to load dynamic username blocklist: {e}")

    regex_bridge = re.compile(REGEX_BRIDGE)
    
    # 2. Iterate ALL messages
    all_msgs_gen = database.get_messages_in_range(CUSTOM_START, CUSTOM_END)
    
    # 30d Filter
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    
    for msg in all_msgs_gen:
        content = msg['content'] or ""
        raw_author = msg['author_name'] or ""
        ts_str = msg['created_at']
        
        # Parse timestamp
        try:
             msg_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00')) if ts_str else datetime.min.replace(tzinfo=timezone.utc)
        except:
             msg_dt = datetime.min.replace(tzinfo=timezone.utc)
        
        real_user_key = None
        message_body = content # Default to full content
        
        # Resolve User
        norm_author = normalize_user_string(raw_author)
        if norm_author in target_users_map:
            real_user_key = target_users_map[norm_author]
        else:
            # Check Bridge
            # Bridge format: "**User** (Rank): Message" OR "**User**: Message"
            matches = regex_bridge.findall(content)
            if matches:
                 m_user = matches[0]
                 norm_m = normalize_user_string(m_user)
                 if norm_m in target_users_map:
                     real_user_key = target_users_map[norm_m]
                     
                     # Extract ACTUAL message body (after the first colon)
                     # This strips "**User** (Rank):" prefix entirely
                     parts = content.split(':', 1)
                     if len(parts) > 1:
                         message_body = parts[1].strip()
                     else:
                         message_body = "" # No content after colon?
        
        if real_user_key and message_body:
            # 3. Filter "Auto-Announcements"
            # If the body looks like a system msg, skip logic
            msg_lower = message_body.lower()
            if any(trigger in msg_lower for trigger in AUTO_ANNOUNCEMENT_TRIGGERS):
                continue

            # A. Question Count (30d Only)
            q_count = message_body.count('?')
            if q_count > 0 and msg_dt >= cutoff_30d:
                user_q_counts[real_user_key] += q_count
                
            # B. Word Analysis
            # 1. Strip Custom Emojis (<:name:id>, <a:name:id>)
            # This handles "unranked_group_ironman_chat_badg" which comes from emoji text
            clean_text = re.sub(r'<a?:[^:]+:\d+>', ' ', msg_lower)
            
            # 2. Clean punctuation
            # Replace underscores with space to split snake_case names if typed safely
            clean_text = re.sub(r'[\W_]', ' ', clean_text)
            
            words = clean_text.split()
            valid_words = []
            for w in words:
                # Skip numeric-ish words
                if w.isdigit(): continue
                # Skip if stop word (unless allowed slang)
                if w not in ALLOWED_SLANG and (w in STOP_WORDS or len(w) < 2):
                    continue
                valid_words.append(w)
                
            if valid_words:
                user_word_counts[real_user_key].update(valid_words)

    # 3. Add to Results
    for u_lower in results:
        # Questions
        results[u_lower]['Questions Asked (30d)'] = user_q_counts[u_lower]
        
        # Fav Word
        top = user_word_counts[u_lower].most_common(1)
        if top:
            results[u_lower]['Favorite Word'] = top[0][0] # The word
        else:
            results[u_lower]['Favorite Word'] = "N/A"

    # Build DataFrame
    final_data = list(results.values())
    df = pd.DataFrame(final_data)
    
    # Sort: Rank Score (Ladder) -> Total XP
    sort_cols = []
    if 'Rank Score' in df.columns:
        sort_cols.append('Rank Score')
    
    xp_key = periods['total']['xp_key']
    if xp_key in df.columns:
        sort_cols.append(xp_key)
        
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
    
    # Add new columns to Ordered List
    ordered_columns.extend(['Questions Asked (30d)', 'Favorite Word'])

    # Save CSV
    safe_save(df, OUTPUT_FILE_CSV, index=False)
    
    # Save Excel
    # Wrapper for Excel permission error
    # wrapper for Excel permission error
    target_xlsx_file = OUTPUT_FILE_XLSX
    try:
        writer = pd.ExcelWriter(target_xlsx_file, engine='xlsxwriter')
    except PermissionError:
         base, ext = os.path.splitext(target_xlsx_file)
         new_name_xlsx = f"{base}_{int(datetime.now().timestamp())}{ext}"
         logging.warning(f"  [WARN] Could not save to '{target_xlsx_file}' (File open?). Saving to '{new_name_xlsx}' instead.")
         writer = pd.ExcelWriter(new_name_xlsx, engine='xlsxwriter')
         target_xlsx_file = new_name_xlsx

    # Important: Reorder columns before saving
    # Filter to only include columns that exist in df and are in ordered_columns
    final_cols = [c for c in ordered_columns if c in df.columns]
    
    # Save Ordered CSV
    df = df[final_cols]
    df.to_csv(OUTPUT_FILE_CSV, index=False)
    
    # Save Excel (Ordered & Formatted)
    try:
        # Note: 'writer' was initialized above (lines 790-796)
        
        df.to_excel(writer, index=False, sheet_name='Summary')
        
        # Access the workbook and worksheet objects
        workbook  = writer.book
        worksheet = writer.sheets['Summary']
        (max_row, max_col) = df.shape
        
        # --- Formatting Definitions ---
        # Colors approximated from user screenshot/request
        # Added 'border': 1 for all cells
        format_header = workbook.add_format({'bold': True, 'bottom': 1, 'border': 1})
        
        # Category Colors
        # Also apply Number Format: '#,##0' (Thousands separator, no decimals)
        base_fmt = {'border': 1, 'num_format': '#,##0'}
        
        color_green = '#C6EFCE'  # Light Green
        color_orange = '#FFEB9C' # Light Orange
        color_yellow = '#FFFFCC' # Light Yellow
        color_blue = '#DCE6F1'   # Pastel Blue (Questions)
        color_purple = '#E4DFEC' # Pastel Purple (Fav Word)
        
        fmt_green = workbook.add_format({**base_fmt, 'bg_color': color_green})
        fmt_orange = workbook.add_format({**base_fmt, 'bg_color': color_orange})
        fmt_yellow = workbook.add_format({**base_fmt, 'bg_color': color_yellow})
        fmt_blue = workbook.add_format({**base_fmt, 'bg_color': color_blue})
        fmt_purple = workbook.add_format({**base_fmt, 'bg_color': color_purple})
        
        # Format Mapping based on Column Name
        for i, col_name in enumerate(df.columns):
            col_lower = col_name.lower()
            target_fmt = None
            
            # Determine Color
            if 'questions' in col_lower:
                target_fmt = fmt_blue
            elif 'favorite' in col_lower or 'word' in col_lower:
                target_fmt = fmt_purple
            elif 'message' in col_lower:
                target_fmt = fmt_orange
            elif 'boss' in col_lower and 'kill' in col_lower:
                target_fmt = fmt_yellow
            else:
                # Default to Green (Username, Role, XP)
                target_fmt = fmt_green
                
            # Auto-fit Width Calculation
            max_len = len(str(col_name)) # Header length
            for val in df[col_name]:
                # For numbers formatted with separators, the string length might inevitably be longer
                # simple len(str(val)) is a decent approximation for unformatted
                v_len = len(str(val))
                if v_len > max_len:
                    max_len = v_len
            
            # Add a little padding
            final_width = max_len + 3
            if final_width > 50: final_width = 50
            
            worksheet.set_column(i, i, final_width, target_fmt)
            
        # --- Freeze Panes ---
        worksheet.freeze_panes(1, 1)

        # --- Conditional Formatting (Zeroes) ---
        if EXCEL_ZERO_HIGHLIGHT:
            # Must preserve border and num_format in conditional highlight too
            red_format = workbook.add_format({
                'bg_color': EXCEL_ZERO_BG_COLOR, 
                'font_color': EXCEL_ZERO_FONT_COLOR,
                'border': 1,
                'num_format': '#,##0'
            })
            
            # Apply to all data cells
            worksheet.conditional_format(1, 0, max_row, max_col - 1, {
                'type': 'cell', 'criteria': '==', 'value': 0, 'format': red_format
            })
            
        worksheet.autofilter(0, 0, max_row, max_col - 1)
        
        # --- SIDEBAR REMOVED AS REQUESTED ---
        
        writer.close()
        logging.info(f"Saved EXCEL: {target_xlsx_file}")
        
    except Exception as e:
         logging.error(f"Failed to save Excel: {e}")

    logging.info("--- Report Generation Complete ---")
    
    # --- 9. Local Drive Sync ---
    LOCAL_DRIVE_PATH = os.getenv('LOCAL_DRIVE_PATH')
    if LOCAL_DRIVE_PATH:
        logging.info(f"--- Syncing to Local Drive: {LOCAL_DRIVE_PATH} ---")
        try:
            # 1. Verify Destination exists
            if not os.path.exists(LOCAL_DRIVE_PATH):
                logging.warning(f"  [WARN] Destination folder does not exist: {LOCAL_DRIVE_PATH}")
                logging.warning("  Attempting to create it...")
                os.makedirs(LOCAL_DRIVE_PATH, exist_ok=True)
            
            # 2. Copy Excel
            dst_xlsx = os.path.join(LOCAL_DRIVE_PATH, OUTPUT_FILE_XLSX)
            # Use 'target_xlsx_file' in case we renamed it due to permission error
            shutil.copy2(target_xlsx_file, dst_xlsx)
            logging.info(f"  [SUCCESS] Copied Excel to: {dst_xlsx}")
            
            # 3. Copy CSV (Optional, but good backup)
            dst_csv = os.path.join(LOCAL_DRIVE_PATH, OUTPUT_FILE_CSV)
            shutil.copy2(OUTPUT_FILE_CSV, dst_csv)
            logging.info(f"  [SUCCESS] Copied CSV to: {dst_csv}")
            
        except Exception as e:
            logging.error(f"  Failed to copy to Drive: {e}")
    else:
         logging.info("LOCAL_DRIVE_PATH not set. Skipping Drive sync.")
         
    if not TEST_MODE:
        logging.info("All tasks finished. Closing in 5 seconds...")
        await asyncio.sleep(5)


async def run_main():
    try:
        await main()
    finally:
        await wom_client.close()

if __name__ == "__main__":
    asyncio.run(run_main())
