"""
REPORTER SCRIPT
===============
This script is responsible for "Analysis and Presentation".
It reads raw data from the local database, performs calculations,
and generates the final Excel report.

Usage:
    python report.py

Core Functions:
1.  Stats Calculation: Calculates XP/Kill gains over time periods (7d, 30d, etc).
2.  Text Analysis: Scans messages for "Favorite Words" and Question counts.
3.  Excel Generation: Creates a formatted .xlsx file.
"""
import asyncio
import logging
import sys
import shutil
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, func
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from core.config import Config
from core.utils import load_json_list, normalize_user_string
from database.connector import SessionLocal, init_db
from database.models import WOMSnapshot, DiscordMessage
from services.wom import wom_client
from reporting.analysis import analyzer
from reporting.excel import reporter

# Setup Logging
from logging.handlers import RotatingFileHandler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler("app.log", maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Report")

async def get_snapshot_before(db, username, target_date):
    """(Legacy) Finds latest snapshot on or before target_date."""
    stmt = select(WOMSnapshot).where(
        WOMSnapshot.username == username,
        WOMSnapshot.timestamp <= target_date
    ).order_by(WOMSnapshot.timestamp.desc()).limit(1)
    return db.execute(stmt).scalars().first()

async def get_snapshots_bulk(db, usernames, target_date):
    """
    Efficiently fetches the latest snapshot on or before target_date for multiple users.
    Returns: Dict[username, WOMSnapshot]
    """
    logger.info(f"   -> Bulk fetching snapshots for {len(usernames)} users before {target_date}...")
    
    # SQLite-compatible approach:
    # 1. Subquery: Get max timestamp per user <= target_date
    # 2. Join: Get rows matching those timestamps
    
    # Subquery: SELECT username, MAX(timestamp) as max_ts FROM wom_snapshots ... GROUP BY username
    subq = (
        select(WOMSnapshot.username, func.max(WOMSnapshot.timestamp).label("max_ts"))
        .where(
            WOMSnapshot.username.in_(usernames),
            WOMSnapshot.timestamp <= target_date
        )
        .group_by(WOMSnapshot.username)
        .subquery()
    )
    
    # Main query: Join snapshots with subquery
    stmt = (
        select(WOMSnapshot)
        .join(subq, and_(
            WOMSnapshot.username == subq.c.username,
            WOMSnapshot.timestamp == subq.c.max_ts
        ))
    )
    
    results = db.execute(stmt).scalars().all()
    
    snapshot_map = {r.username: r for r in results}
    logger.info(f"   -> Found snapshots for {len(snapshot_map)} users via bulk query.")
    return snapshot_map

def count_messages(db, start_dt, end_dt, target_users):
    """Counts messages per user in range."""
    logger.info(f"Counting messages between {start_dt} and {end_dt}...")
    
    stmt = select(DiscordMessage).where(
        DiscordMessage.created_at >= start_dt,
        DiscordMessage.created_at <= end_dt
    )
    msgs = db.execute(stmt).scalars().all()
    logger.info(f" -> Found {len(msgs)} messages in this period.")
    
    counts = {u: 0 for u in target_users}
    user_map = {normalize_user_string(u): u for u in target_users}
    
    import re
    regex = re.compile(r"\*\*(.+?)\*\*:")
    
    for m in msgs:
        content = m.content or ""
        author = m.author_name or ""
        
        # 1. Author
        norm = normalize_user_string(author)
        if norm in user_map:
            counts[user_map[norm]] += 1
            continue
            
        # 2. Bridge
        matches = regex.findall(content)
        if matches:
            norm_b = normalize_user_string(matches[0])
            if norm_b in user_map:
                counts[user_map[norm_b]] += 1
                
    return counts

async def backfill_missing_history(db, username):
    """
    Fetches full snapshot history for a user and saves it to the DB.
    Used when local data is missing for a required period.
    """
    try:
        # logger.info(f"   -> Backfilling history for {username}...")
        snapshots = await wom_client.get_player_snapshots(username)
        
        if not snapshots:
            return 0
            
        # Bulk check existing to avoid unique constraint errors (if any)
        # Though our model doesn't enforce unique (username, timestamp) yet, it's good practice.
        # Ideally we fetch all timestamps for user to skip.
        
        # Optimization: Just fetch timestamps for this user
        existing_stm = select(WOMSnapshot.timestamp).where(WOMSnapshot.username == username.lower())
        existing_ts = set(db.execute(existing_stm).scalars().all())
        
        new_snapshots = []
        for s in snapshots:
            ts_str = s.get('createdAt')
            if not ts_str: continue
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except:
                continue
                
            # Naive/Aware check - assumming DB is naive UTC or consistent
            # To be safe, compare timestamps using the same timezone info logic as backfill.py
            if ts.tzinfo is not None:
                ts_naive = ts.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                ts_naive = ts

            # We can't easily check against DB timestamps if mix of aware/naive in set.
            # But let's assume standard behavior.
            # A simpler way is to try/except integrity error if we had constraints, but we don't.
            # So we rely on strict timestamp check. 
            
            # Let's just do a rough check. If we are running this, it's because we missed data.
            # We assume the user might have some data but not the needed one.
            
            # Correction: simple "if ts in existing_ts" might fail on microsecond precision or tz.
            # Let's rely on the fact that if we are here, we probably want to save whatever we got.
            # BUT we don't want duplicates.
            
            # Check against set
            # Converting retrieved DB timestamps to aware UTC for comparison if needed
            # For now, let's skip complex dedup here and rely on the fact that 
            # we usually run this only if data is MISSING. 
            # Wait, if we have recent data but missing old data, we don't want to re-insert recent data.
            
            # Let's match backfill.py logic:
            # existing_ts is from DB.
            is_duplicate = False
            for ets in existing_ts:
                if abs((ets - ts_naive).total_seconds()) < 1: 
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue

            data = s.get('data', {})
            bosses = data.get('bosses', {})
            total_boss_kills = sum(b.get('kills', 0) for b in bosses.values() if b.get('kills', 0) > 0)
            
            snap = WOMSnapshot(
                username=username.lower(),
                timestamp=ts,
                total_xp=data.get('skills', {}).get('overall', {}).get('experience', 0),
                total_boss_kills=total_boss_kills,
                ehp=s.get('ehp', 0),
                ehb=s.get('ehb', 0),
                raw_data=json.dumps(s)
            )
            new_snapshots.append(snap)
            
        if new_snapshots:
            db.add_all(new_snapshots)
            db.commit()
            return len(new_snapshots)
            
    except Exception as e:
        logger.error(f"Error backfilling {username}: {e}")
    
    return 0

async def main():
    logger.info("==========================================")
    logger.info("       STARTING REPORT GENERATION         ")
    logger.info("==========================================")
    db = SessionLocal()
    
    try:
        # 1. Get Members
        logger.info(f"Fetching group members from WOM (Group ID: {Config.WOM_GROUP_ID})...")
        members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
        logger.info(f" -> Successfully fetched {len(members)} members.")
        
        member_usernames = [m['username'].lower() for m in members]
        role_map = {m['username'].lower(): m['role'] for m in members}
        join_date_map = {m['username'].lower(): m.get('joined_at') for m in members}
        
        # DEBUG: Log some roles to check for mismatches
        debug_roles = {k: role_map[k] for k in list(role_map.keys())[:5]}
        logger.info(f"[DEBUG] Sample Roles from WOM: {debug_roles}")
        
        # 2. Define Periods
        now = datetime.now()
        periods = {
            '7d': {'start': now - timedelta(days=7), 'end': now},
            '30d': {'start': now - timedelta(days=30), 'end': now},
            '70d': {'start': now - timedelta(days=70), 'end': now},
            '150d': {'start': now - timedelta(days=150), 'end': now}
        }
        
        custom_start = datetime.fromisoformat(Config.CUSTOM_START_DATE)
        periods['Total'] = {'start': custom_start, 'end': now}
        logger.info(f"Defined {len(periods)} reporting periods.")
        
        # 3. Get Current Snapshots
        logger.info("Fetching latest local snapshots for all members to calculate current stats...")
        current_snapshots = await get_snapshots_bulk(db, member_usernames, now)
        logger.info(f" -> Found local snapshots for {len(current_snapshots)}/{len(member_usernames)} members.")

        # 3.5. Get Earliest Snapshots (Optimization & Partial Interval Handling)
        logger.info("Fetching full earliest snapshots for all members...")
        # Subquery for min timestamp
        subq_min = (
            select(WOMSnapshot.username, func.min(WOMSnapshot.timestamp).label("min_ts"))
            .group_by(WOMSnapshot.username)
            .subquery()
        )
        # Join to get full row
        stmt_first = (
            select(WOMSnapshot)
            .join(subq_min, and_(
                WOMSnapshot.username == subq_min.c.username,
                WOMSnapshot.timestamp == subq_min.c.min_ts
            ))
        )
        first_snapshots_list = db.execute(stmt_first).scalars().all()
        first_snapshots_map = {s.username: s for s in first_snapshots_list}
        logger.info(f" -> Found earliest snapshots for {len(first_snapshots_map)} users.")

        # --- DATA INTEGRITY CHECK ---
        coverage = len(current_snapshots) / len(member_usernames) if members else 0
        if coverage < 0.80:
            msg = f"CRITICAL: Insufficient data! Only {len(current_snapshots)}/{len(members)} ({coverage:.1%}) members have valid snapshots for today. Report generation ABORTED to prevent 'zero data' errors."
            logger.error(msg)
            # You might want to trigger a 'harvest' here, or just fail safely.
            # For now, we return to safely stop without generating a bad file.
            return
        # ----------------------------

        # 4. Calculate Data
        results = {}
        
        ROLE_WEIGHTS = {
            'owner': 100, 'deputy_owner': 90, 'zenyte': 80, 'dragonstone': 80,
            'administrator': 70, 'saviour': 60, 'prospector': 10, 'guest': 0
        }
        
        # Init results structure
        for u in member_usernames:
            role = role_map.get(u, 'member')
            # Parse join date
            j_str = join_date_map.get(u)
            j_date_display = ""
            if j_str:
                try:
                    # ISO format: 2025-02-14T12:45:18.239Z
                    dt = datetime.fromisoformat(j_str.replace("Z", "+00:00"))
                    j_date_display = dt.strftime("%d-%m-%Y")
                except:
                    j_date_display = j_str # Fallback

            results[u] = {
                'Username': u,
                'Joined date': j_date_display,
                'Role': role
            }
            
        logger.info("Starting period calculations...")
        for pid, dates in periods.items():
            logger.info(f"--- Processing Period: {pid} ---")
            s, e = dates['start'], dates['end']
            
            # A. Messages
            msg_counts = count_messages(db, s, e, member_usernames)
            msg_key = f"Messages {pid}" if pid != 'Total' else "Total Messages"
            
            # A2. Old Snapshots (Bulk optimized)
            logger.info(f"Bulk fetching historical snapshots for {pid} start date...")
            old_snapshots = await get_snapshots_bulk(db, member_usernames, s)
            
            # B. Gains
            logger.info(f"Calculating XP/Boss Gains for {pid}...")
            xp_key = f"XP Gained {pid}" if pid != 'Total' else "Total xp gained"
            boss_key = f"Boss kills {pid}" if pid != 'Total' else "Total boss kills"
            
            count_api_fallback = 0
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total} Users"),
                console=Console()
            ) as progress:
                task_id = progress.add_task(f"[green]Calculating {pid}...", total=len(member_usernames))

                for i, u in enumerate(member_usernames):
                    progress.advance(task_id)
                
                    results[u][msg_key] = msg_counts.get(u, 0)
                    
                    # Gains
                    curr = current_snapshots.get(u)
                    if not curr:
                        results[u][xp_key] = 0
                        results[u][boss_key] = 0
                        continue
                        
                    old = old_snapshots.get(u)
                    
                    if old:
                        # Delta
                        results[u][xp_key] = curr.total_xp - (old.total_xp or 0)
                        results[u][boss_key] = curr.total_boss_kills - (old.total_boss_kills or 0)
                    else:
                        # Old snapshot (<= start_date) is missing.
                        # This usually means the user joined the tracking *after* the start date.
                        
                        # SMART BASELINE CHECK:
                        # Use the user's earliest known snapshot as the baseline if available.
                        first_snap = first_snapshots_map.get(u)
                        
                        should_backfill = True
                        
                        if first_snap and first_snap.timestamp > s:
                            # We have data, but it's newer than the target start date.
                            # Just use this earliest data as the baseline.
                            # Gain = Current - Earliest
                            results[u][xp_key] = curr.total_xp - (first_snap.total_xp or 0)
                            results[u][boss_key] = curr.total_boss_kills - (first_snap.total_boss_kills or 0)
                            should_backfill = False
                            # logger.debug(f"Using partial period for {u}: First ({first_snap.timestamp}) > Start ({s})")
                        
                        if should_backfill:
                            # We have NO data at all (or logically implies we might have earlier data not yet fetched?)
                            # Actually if first_snap exists and is > s, we entered the block above.
                            # So we only reach here if first_snap is None? 
                            # Or if first_snap <= s but somehow old_snapshots didn't pick it up? (Impossible logic-wise if queries are correct)
                            # Effectively this runs if user is missing from DB mostly.
                            
                            if count_api_fallback == 0:
                                logger.info(f"   (Local data missing for {u}. auto-fetching history...)")
                            count_api_fallback += 1
                            
                            # 1. Fetch & Save
                            added = await backfill_missing_history(db, u)
                            
                            # 2. Retry fetching local snapshot
                            old_retry = await get_snapshot_before(db, u, s)
                            
                            if old_retry:
                                 results[u][xp_key] = curr.total_xp - (old_retry.total_xp or 0)
                                 results[u][boss_key] = curr.total_boss_kills - (old_retry.total_boss_kills or 0)
                            else:
                                # Still missing? Maybe just joined?
                                # Try fallback to earliest again
                                # Re-fetch earliest since we just added data
                                stmt_retry_first = select(WOMSnapshot).where(WOMSnapshot.username == u).order_by(WOMSnapshot.timestamp.asc()).limit(1)
                                first_retry = db.execute(stmt_retry_first).scalars().first()
                                
                                if first_retry:
                                    results[u][xp_key] = curr.total_xp - (first_retry.total_xp or 0)
                                    results[u][boss_key] = curr.total_boss_kills - (first_retry.total_boss_kills or 0)
                                else:
                                    results[u][xp_key] = 0
                                    results[u][boss_key] = 0
            
            if count_api_fallback > 0:
                logger.info(f"   -> Triggered auto-backfill for {count_api_fallback} users.")

        # 5. Text Stats (30d)
        logger.info("--- Analyzing Text Stats (30d) ---")
        text_stats = analyzer.analyze_30d(member_usernames)
        for u, stats in text_stats.items():
            if u in results:
                results[u]['Questions Asked (30d)'] = stats['questions']
                results[u]['Favorite Word'] = stats['fav_word']
        logger.info("Text analysis complete.")
        
        
        # 6. Generate Excel
        logger.info("--- Generating Excel Report ---")
        data_list = list(results.values())
        reporter.generate(data_list)
        logger.info("Excel report generated successfully.")

        # 6.5. Sync to Google Drive
        if Config.LOCAL_DRIVE_PATH:
            logger.info(f"--- Syncing to Google Drive ({Config.LOCAL_DRIVE_PATH}) ---")
            if os.path.exists(Config.LOCAL_DRIVE_PATH):
                try:
                    src = Config.OUTPUT_FILE_XLSX
                    dst = os.path.join(Config.LOCAL_DRIVE_PATH, src)
                    shutil.copy2(src, dst)
                    logger.info(f" -> Successfully copied report to: {dst}")
                except Exception as e:
                    logger.error(f" -> Failed to copy to Drive: {e}")
            else:
                logger.warning(f" -> Drive path not found: {Config.LOCAL_DRIVE_PATH}")
        
        # 7. Send Discord Embed (Rec 3)
        if Config.RELAY_CHANNEL_ID and Config.DISCORD_TOKEN:
            try:
                from services.discord import discord_service
                # Construct simple stats
                # Top Gainer logic
                # Sort by 'Total xp gained'
                sorted_res = sorted(data_list, key=lambda x: x.get('Total xp gained', 0), reverse=True)
                top_gainer = sorted_res[0] if sorted_res else {'Username': 'None', 'Total xp gained': 0}
                
                # Active chatter
                sorted_msg = sorted(data_list, key=lambda x: x.get('Total Messages', 0), reverse=True)
                top_chatter = sorted_msg[0] if sorted_msg else {'Username': 'None', 'Total Messages': 0}
                
                stats_summary = {
                    "🥇 Top XP (All Time)": f"{top_gainer['Username']} ({top_gainer.get('Total xp gained', 0):,})",
                    "🗣️ Chatterbox": f"{top_chatter['Username']} ({top_chatter.get('Total Messages', 0):,})",
                    "👥 Active Members": f"{len(data_list)}"
                }
                
                # We need to run this output async, main is async
                # logger.info("Sending Discord Summary...")
                # await discord_service.send_summary_embed(Config.RELAY_CHANNEL_ID, stats_summary)
            except Exception as e:
                logger.error(f"Failed to trigger Discord Embed: {e}")
                
        logger.info("==========================================")
        logger.info("       REPORT GENERATION COMPLETE         ")
        logger.info("==========================================")
        
    finally:
        db.close()
        await wom_client.close()

if __name__ == "__main__":
    asyncio.run(main())
