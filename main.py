import asyncio
import os
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
load_dotenv()

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
    end_str = os.getenv('CUSTOM_END_DATE', '2025-12-08')
    try:
        s = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        e = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        return s, e
    except:
        # Fallback
        return datetime(2025, 2, 14, tzinfo=timezone.utc), datetime(2025, 12, 8, tzinfo=timezone.utc)

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
    
    # Reuse existing Summary Table Logic (Joined/Left/Top 3)
    # We need to fetch activity logs again? Yes.
    
    joined_30d = []
    left_30d = []
    
    # [Activity Fetch]
    cutoff_30d = now - timedelta(days=30)
    # Fetch more at once
    try:
        act_logs = await wom_client.get_group_activity(WOM_GROUP_ID, limit=50) 
        if act_logs:
            for log in act_logs:
                try:
                    ts_str = log['createdAt']
                    if ts_str.endswith('Z'): ts_str = ts_str[:-1] + '+00:00'
                    log_date = datetime.fromisoformat(ts_str)
                    if log_date > cutoff_30d:
                        p_name = log.get('player', {}).get('displayName', 'Unknown')
                        if log['type'] == 'member_joined':
                            joined_30d.append(f"{p_name} ({log_date.strftime('%Y-%m-%d')})")
                        elif log['type'] == 'member_left':
                            left_30d.append(f"{p_name} ({log_date.strftime('%Y-%m-%d')})")
                except: pass
    except Exception as e:
        logging.error(f"Error fetching activity logs: {e}")

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
    df = df[final_cols]

    df.to_excel(writer, index=False, sheet_name='Summary')
    
    # Formatting
    workbook = writer.book
    worksheet = writer.sheets['Summary']
    (max_row, max_col) = df.shape
    
    # --- Formatting Definitions ---
    # Colors approximated from user screenshot/request
    format_header = workbook.add_format({'bold': True, 'bottom': 1})
    
    # Category Colors
    color_green = '#C6EFCE'  # Light Green (User, Role, XP)
    color_orange = '#FFEB9C' # Light Orange (Messages) - Adjusted to look like screenshot
    color_yellow = '#FFFFCC' # Light Yellow (Boss Kills)
    
    fmt_green = workbook.add_format({'bg_color': color_green})
    fmt_orange = workbook.add_format({'bg_color': color_orange})
    fmt_yellow = workbook.add_format({'bg_color': color_yellow})
    
    # Format Mapping based on Column Name
    # We iterate columns and apply format to the whole column (excluding header potentially, but add_format applies to cells)
    # Actually set_column applied to range.
    
    for i, col_name in enumerate(df.columns):
        col_lower = col_name.lower()
        target_fmt = None
        
        # Determine Color
        if 'message' in col_lower:
            target_fmt = fmt_orange
        elif 'boss' in col_lower and 'kill' in col_lower:
            target_fmt = fmt_yellow
        else:
            # Default to Green (Username, Role, XP)
            target_fmt = fmt_green
            
        # Write the column with the format (offset by 1 for index if needed, but we use A1 notation or set_column)
        # set_column(first_col, last_col, width, cell_format)
        # formatting applied here is the Default for the column. 
        # Conditional formatting (Red for 0) will override this if valid.
        
        # Auto-fit Width Calculation
        # Get max length of data in this column
        max_len = len(str(col_name)) # Header length
        for val in df[col_name]:
            v_len = len(str(val))
            if v_len > max_len:
                max_len = v_len
        
        # Add a little padding
        final_width = max_len + 2
        
        # Cap width just in case
        if final_width > 50: final_width = 50
        
        worksheet.set_column(i, i, final_width, target_fmt)
        
    # --- Freeze Panes ---
    # Freeze Top Row (1) and First Column (A)
    worksheet.freeze_panes(1, 1)

    # --- Conditional Formatting (Zeroes) ---
    # This applies ON TOP of the cell formatting
    if EXCEL_ZERO_HIGHLIGHT:
        red_format = workbook.add_format({'bg_color': EXCEL_ZERO_BG_COLOR, 'font_color': EXCEL_ZERO_FONT_COLOR})
        
        # Apply to all data cells
        worksheet.conditional_format(1, 0, max_row, max_col - 1, {
            'type': 'cell', 'criteria': '==', 'value': 0, 'format': red_format
        })
        
    worksheet.autofilter(0, 0, max_row, max_col - 1)
    
    # Summary Table Construction (Top Lists)
    # Re-calculate Top 3 for XP, Msg, EHP if available
    summary_data = [["Usefull Stats (30d)", "Player List"]]
    
    # Messages
    top_msg_key = periods['30d']['msg_key']
    if top_msg_key in df.columns:
        top = df.nlargest(3, top_msg_key)[['Username', top_msg_key]]
        summary_data.append(["Highest Msg Count:", ""])
        for rank, (_, r) in enumerate(top.iterrows(), 1): summary_data.append(["", f"{rank}. {r['Username']} ({r[top_msg_key]})"])
    
    summary_data.append(["", ""])
    
    # XP
    top_xp_key = periods['30d']['xp_key']
    if top_xp_key in df.columns:
        top = df.nlargest(3, top_xp_key)[['Username', top_xp_key]]
        summary_data.append(["Highest XP Gained:", ""])
        for rank, (_, r) in enumerate(top.iterrows(), 1): summary_data.append(["", f"{rank}. {r['Username']} ({r[top_xp_key]})"])

    # Joined/Left
    summary_data.append(["", ""])
    summary_data.append(["Players Joined:", ""])
    for p in (joined_30d or ["None"]): summary_data.append(["", p])
    
    summary_data.append(["", ""])
    summary_data.append(["Players Left:", ""])
    for p in (left_30d or ["None"]): summary_data.append(["", p])

    # Write Summary
    start_col = max_col + 2
    bold_fmt = workbook.add_format({'bold': True})
    
    for r, row in enumerate(summary_data):
        fmt = bold_fmt if row[0] else None
        worksheet.write(r, start_col, row[0], fmt)
        worksheet.write(r, start_col+1, row[1])
        
    worksheet.set_column(start_col, start_col+1, 25)
    
    writer.close()
    logging.info(f"Saved Excel: {target_xlsx_file}")
    logging.info("Done!")

async def run_main():
    try:
        await main()
    finally:
        await wom_client.close()

if __name__ == "__main__":
    asyncio.run(run_main())
