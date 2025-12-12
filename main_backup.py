import asyncio
import os
import csv
import pandas as pd
import re
import database # [NEW] Import database module
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

# --- Test Configuration ---
TEST_MODE = False         # Set to False for full run
TEST_PLAYER_LIMIT = 20    # Number of players to process in test mode

# Date Ranges
CUSTOM_START = datetime(2025, 2, 14, tzinfo=timezone.utc)
CUSTOM_END = datetime(2025, 12, 8, tzinfo=timezone.utc)

# Regex for Bridge Bot (if used)
REGEX_BRIDGE = r"\*\*(.+?)\*\*:"

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
    print("\n--- Syncing Discord Messages (Database) ---")
    
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
            print(f"  [Backfill] Gap detected! DB starts at {earliest_dt}, need data from {start_backfill_target}")
            print(f"  Fetching missing history: {start_backfill_target} -> {earliest_dt}")
            # Fetch older messages (reverse chronological usually, but our bot handles ranges)
            gap_msgs = await run_discord_fetch(start_date=start_backfill_target, end_date=earliest_dt)
            if gap_msgs:
                count, skipped = database.insert_messages(gap_msgs)
                print(f"  [Backfill] Inserted {count} older messages (Skipped {skipped} duplicates).")
            else:
                print("  [Backfill] No messages found in gap.")
        else:
            print(f"  [Backfill] History looks complete (Starts: {earliest_dt}).")
    else:
        # DB is empty, will be handled by forward sync or initial fetch
        print("  Database empty. Initializing full fetch...")
        latest_ts = None # Trigger full fetch below logic if we want, or set start date
        # Actually if empty, we should just set the start date to CUSTOM_START for the forward sync
    
    # --- B. Forward Sync (New Messages) ---
    start_fetch_date = None
    if latest_ts:
        if latest_ts.endswith('Z'): latest_ts = latest_ts[:-1] + '+00:00'
        start_fetch_date = datetime.fromisoformat(latest_ts)
        print(f"  [Forward] Last DB message: {start_fetch_date}")
    else:
        # If empty, start from CUSTOM_START
        start_fetch_date = start_backfill_target
        print(f"  [Forward] Starting fresh fetch from: {start_fetch_date}")

    print(f"  [Forward] Fetching new messages since {start_fetch_date}...")
    new_msgs = await run_discord_fetch(start_date=start_fetch_date, end_date=None)
    
    if new_msgs:
        count, skipped = database.insert_messages(new_msgs)
        print(f"  [Forward] Inserted {count} new messages (Skipped {skipped} duplicates).")
    else:
        print("  [Forward] No new messages found.")

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

async def fetch_wom_gains(group_id, start_dt, end_dt):
    """
    Fetches WOM XP gains for the group within the window.
    Returns dict: {username_lower: xp_gained}
    """
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()
    print(f"  Fetching WOM gains ({start_dt.date()} to {end_dt.date()})...")
    
    xp_map = {}
    
    try:
        all_gains = []
        # Prepare params
        params = {
            'metric': 'overall',
            'startDate': start_iso,
            'endDate': end_iso
        }
        
        # Limit processing if TEST_MODE
        limit = TEST_PLAYER_LIMIT if TEST_MODE else 50
        max_pages = 1 if TEST_MODE else None

        # Use helper
        all_gains = await wom_client.fetch_paginated(
            f'/groups/{group_id}/gained', 
            params=params, 
            limit=limit,
            max_pages=max_pages
        )
            
        print(f"    Fetched gains for {len(all_gains)} players.")
        
        for p in all_gains:
            username = p['player']['username'].lower()
            xp = p['data']['gained']
            xp_map[username] = xp
            
    except Exception as e:
        print(f"    Error fetching WOM data: {e}")
        
    return xp_map

async def main():
    if not WOM_GROUP_ID:
        print("Error: WOM_GROUP_ID not set.")
        return

    # --- 0. Trigger Group Update ---
    WOM_GROUP_SECRET = '728834546'
    print(f"\n--- Triggering WOM Group Update (ID: {WOM_GROUP_ID}) ---")
    try:
        resp = await wom_client.update_group(WOM_GROUP_ID, WOM_GROUP_SECRET)
        print(f"  Update triggered: {resp.get('message', 'Success')}")
        print("  Waiting 5 minutes for update to propagate...")
        await asyncio.sleep(300) # 300 seconds = 5 minutes
    except Exception as e:
        print(f"  Error updating group (proceeding anyway): {e}")

    # --- 1. Master Discord Sync (DB) ---
    await update_discord_db()
    
    # --- 2. Get Group Members ---
    print("\n--- Fetching WOM Members ---")
    members_data = await wom_client.get_group_members(WOM_GROUP_ID)
    # List of original usernames
    member_usernames = [m['username'] for m in members_data]
    print(f"  Found {len(member_usernames)} members.")
    
    if TEST_MODE:
        print(f"  [TEST MODE] Limiting to first {TEST_PLAYER_LIMIT} members for processing.")
        member_usernames = member_usernames[:TEST_PLAYER_LIMIT]
    
    # --- 3. Define Periods ---
    now = datetime.now(timezone.utc)
    
    periods = {
        '30d': {
            'start': now - timedelta(days=30),
            'end': now,
            'xp_key': 'XP Gained (30d)',
            'msg_key': 'Messages (30d)'
        },
        '150d': {
            'start': now - timedelta(days=150),
            'end': now,
            'xp_key': 'XP Gained (150d)',
            'msg_key': 'Messages (150d)'
        },
        'custom': {
            'start': CUSTOM_START,
            'end': CUSTOM_END,
            'xp_key': 'Total XP (Feb-Dec)',
            'msg_key': 'Total Messages (Feb-Dec)'
        }
    }
    
    # Prepare Result Structure
    results = {}
    for u in member_usernames:
        results[u.lower()] = {'Username': u}
        for p in periods.values():
            results[u.lower()][p['xp_key']] = 0
            results[u.lower()][p['msg_key']] = 0
            
    # --- 4. Process Each Period ---
    print("\n--- Processing Data Periods ---")
    for pid, info in periods.items():
        print(f"Processing '{pid}'...")
        
        # A. Discord Counts (Query DB)
        msg_counts = count_messages_in_db_range(info['start'], info['end'], member_usernames)
        
        # B. WOM Gains (Fetch API)
        xp_gains = await fetch_wom_gains(WOM_GROUP_ID, info['start'], info['end'])
        
        # C. Update Results
        for u_lower, data in results.items():
            if u_lower in msg_counts:
                data[info['msg_key']] = msg_counts[u_lower]
            if u_lower in xp_gains:
                data[info['xp_key']] = xp_gains[u_lower]

    # --- 5. Enhanced Reporting (Activity & Top Lists) ---
    print("\n--- Generating Enhanced Reports ---")
    
    # A. Fetch Activity Logs (Joined/Left)
    print("  Fetching Group Activity Logs...")
    
    joined_30d = []
    left_30d = []
    cutoff_30d = now - timedelta(days=30)
    
    # Pagination loop for activity
    act_limit = 50 # Lower limit to be safe
    act_offset = 0
    keep_fetching = True
    
    while keep_fetching:
        try:
            # We must use correct params for pagination if WOM supports it on /activity
            # WOM Groups Activity endpoint supports ?limit=X&offset=Y
            logs = await wom_client.get_group_activity(WOM_GROUP_ID, limit=act_limit, offset=act_offset)
            
            if not logs:
                break
                
            for log in logs:
                # Log structure parsing
                try:
                    ts_str = log['createdAt']
                    if ts_str.endswith('Z'): ts_str = ts_str[:-1] + '+00:00'
                    log_date = datetime.fromisoformat(ts_str)
                    
                    if log_date < cutoff_30d:
                        keep_fetching = False
                        # Don't break immediately, process the rest of this batch? 
                        # Actually standard practice is stop processing once we hit older dates
                        # assuming logs are sorted desc. WOM logs are usually DESC.
                        continue 
                        
                    ltype = log.get('type')
                    player_name = log.get('player', {}).get('displayName', 'Unknown')
                    
                    if ltype == 'member_joined':
                        msg = f"{player_name} ({log_date.strftime('%Y-%m-%d')})"
                        joined_30d.append(msg)
                        print(f"      [Activity] FOUND: {player_name} JOINED on {log_date.strftime('%Y-%m-%d')}")
                    elif ltype == 'member_left':
                        msg = f"{player_name} ({log_date.strftime('%Y-%m-%d')})"
                        left_30d.append(msg)
                        print(f"      [Activity] FOUND: {player_name} LEFT on {log_date.strftime('%Y-%m-%d')}")
                        
                except Exception as e:
                    pass
            
            if not keep_fetching:
                break
                
            if len(logs) < act_limit:
                break # End of data
                
            act_offset += act_limit
            # Safety brake
            if act_offset > 500: 
                print("  Reached activity fetch safety limit (500).")
                break
                
        except Exception as e:
            print(f"  Error fetching activity batch: {e}")
            break

    # B. Calculate Top 3
    final_data = list(results.values())
    df = pd.DataFrame(final_data)
    
    # Sort for Report (Custom XP)
    sort_key = periods['custom']['xp_key']
    df = df.sort_values(by=sort_key, ascending=False)
    
    # Top 3 Messages (30d)
    top_msg_key = periods['30d']['msg_key']
    top_msg = df.nlargest(3, top_msg_key)[['Username', top_msg_key]]
    top_msg_list = [f"{r['Username']} ({r[top_msg_key]})" for _, r in top_msg.iterrows()]
    
    # Top 3 XP (30d)
    top_xp_key = periods['30d']['xp_key']
    top_xp = df.nlargest(3, top_xp_key)[['Username', top_xp_key]]
    top_xp_list = [f"{r['Username']} ({r[top_xp_key]})" for _, r in top_xp.iterrows()]
    
    # --- 6. Export ---
    
    # Save Snapshot to DB
    database.insert_wom_snapshot(final_data)
    
    # CSV (Main Data Only)
    df.to_csv(OUTPUT_FILE_CSV, index=False)
    print(f"Saved CSV: {OUTPUT_FILE_CSV}")
    
    # Excel (Main + Summary)
    writer = pd.ExcelWriter(OUTPUT_FILE_XLSX, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Summary')
    
    workbook = writer.book
    worksheet = writer.sheets['Summary']
    (max_row, max_col) = df.shape
    
    columns = df.columns.tolist()
    xp_indices = [i for i, col in enumerate(columns) if 'XP' in col]
    msg_indices = [i for i, col in enumerate(columns) if 'Messages' in col or 'Msg' in col]
    
    # Red Highlight for 0s (Inactive)
    red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    
    for col_idx in range(1, max_col): # Skip Username column
        # Highlight equal to 0
        worksheet.conditional_format(1, col_idx, max_row, col_idx, {
            'type': 'cell',
            'criteria': '==',
            'value': 0,
            'format': red_format
        })
        
    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, max_row, max_col - 1)
    worksheet.set_column(0, 0, 20)
    worksheet.set_column(1, max_col - 1, 15)
    
    # --- Summary Table (Right Side) ---
    summary_start_col = max_col + 2 # Skip 2 columns
    
    # Headers
    headers = [
        "Usefull Stats (30d)", "Player List"
    ]
    
    # Prepare rows for Metrics
    summary_data = []
    
    # 1. Joined
    summary_data.append(["Players Joined:", ""])
    if joined_30d:
        for p in joined_30d: summary_data.append(["", p])
    else:
        summary_data.append(["", "None"])
        
    summary_data.append(["", ""]) # Spacer
    
    # 2. Left
    summary_data.append(["Players Left:", ""])
    if left_30d:
        for p in left_30d: summary_data.append(["", p])
    else:
        summary_data.append(["", "None"])
        
    summary_data.append(["", ""]) # Spacer

    # 3. Top 3 Messages
    summary_data.append(["Highest Msg Count:", ""])
    for p in top_msg_list: summary_data.append(["", p])
    
    summary_data.append(["", ""]) # Spacer

    # 4. Top 3 XP
    summary_data.append(["Highest XP Gained:", ""])
    for p in top_xp_list: summary_data.append(["", p])

    # Write Summary Table
    # Bold format
    bold_fmt = workbook.add_format({'bold': True})
    
    # Write Headers
    worksheet.write(0, summary_start_col, headers[0], bold_fmt)
    worksheet.write(0, summary_start_col+1, headers[1], bold_fmt)
    
    # Write Data
    for r_idx, row in enumerate(summary_data):
        # If first cell has text, it's a "Header" row in our usage -> Bold it
        fmt = bold_fmt if row[0] else None
        worksheet.write(r_idx + 1, summary_start_col, row[0], fmt)
        worksheet.write(r_idx + 1, summary_start_col + 1, row[1])
        
    # Adjust width
    worksheet.set_column(summary_start_col, summary_start_col, 20)
    worksheet.set_column(summary_start_col + 1, summary_start_col + 1, 30)
    
    writer.close()
    print(f"Saved Excel: {OUTPUT_FILE_XLSX}")
    print("Done!")

async def run_main():
    try:
        await main()
    finally:
        await wom_client.close()

if __name__ == "__main__":
    asyncio.run(run_main())
