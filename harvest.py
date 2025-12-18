"""
HARVESTER SCRIPT
================
This script is responsible for the "Heavy Lifting" of data collection.
It connects to external APIs (Discord, Wise Old Man) and saves raw data
into the local SQLite database.

Usage:
    python harvest.py

Core Functions:
1.  WOM Snapshots: Fetches latest stats for all clan members.
2.  Discord Messages: Fetches history from configured channels.
3.  Name Change Detection: Checks if any member changed their name.
"""
import asyncio
import logging
import sys
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from core.config import Config
from core.utils import normalize_user_string
from core.performance import PerformanceMonitor, timed_operation
from services.wom import wom_client
from services.discord import discord_service
from database.connector import SessionLocal, init_db
from database.models import WOMSnapshot, WOMRecord

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler("app.log", maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Harvest")
console = Console()

@timed_operation("WOM Snapshots Processing")
async def process_wom_snapshots(group_id, members_list):
    """Fetches full player details for all members and saves snapshots."""
    logger.info(f"Processing WOM snapshots for {len(members_list)} members...")
    
    db = SessionLocal()
    
    # Pre-fetch today's snapshots to skip
    today_prefix = datetime.now(timezone.utc).isoformat()[:10]
    
    async def fetch_one(username):
        u_clean = normalize_user_string(username)
        
        # 1. Fetch
        try:
            p = await wom_client.get_player_details(u_clean)
            
            # Parse
            snap = p.get('latestSnapshot') or {}
            data_block = snap.get('data') or {}
            
            # Bosses
            bosses = data_block.get('bosses') or {}
            total_boss_kills = sum(b.get('kills', 0) for b in bosses.values() if b.get('kills', 0) > 0)
            
            # Stats
            ehp = p.get('ehp', 0)
            ehb = p.get('ehb', 0)
            xp = data_block.get('skills', {}).get('overall', {}).get('experience', 0)
            
            import json
            return (u_clean, xp, total_boss_kills, ehp, ehb, json.dumps(p))
            
        except Exception as e:
            return None

    # --- DAILY LOCK OPTIMIZATION ---
    today_date = datetime.now(timezone.utc).date()
    # Find users who already have a snapshot today
    from sqlalchemy import func
    stmt = select(WOMSnapshot.username).where(func.date(WOMSnapshot.timestamp) == str(today_date))
    already_done = set(db.execute(stmt).scalars().all())
    
    target_members = []
    for m in members_list:
        if normalize_user_string(m['username']) in already_done:
            pass # Skip
        else:
            target_members.append(m)
            
    skipped_count = len(members_list) - len(target_members)
    if skipped_count > 0:
        logger.info(f"Skipping {skipped_count} users (Daily Lock active: Snapshots already exist for today).")
    
    if not target_members:
        logger.info("All members up to date. No API calls needed.")
        db.close()
        return

    tasks = [fetch_one(m['username']) for m in target_members]
    results = []
    
    # Rich Progress Bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task_id = progress.add_task("[cyan]Fetching WOM Snapshots...", total=len(tasks))
        
        for f in asyncio.as_completed(tasks):
            res = await f
            if res:
                results.append(res)
            progress.advance(task_id)
            
    # Batch Save
    try:
        count = 0 
        timestamp = datetime.now(timezone.utc)
        
        from database.models import SkillSnapshot, BossSnapshot, WOMSnapshot # Import inside function to avoid circular imports if any
        
        for r in results:
            # r = (username, xp, boss_kills, ehp, ehb, json_str)
            # We need to parse json_str again or pass the dict? 
            # In fetch_one, we return json.dumps(p). 
            # It's better to parse `r[5]` here.
            
            raw_json = r[5]
            snapshot = WOMSnapshot(
                username=r[0],
                timestamp=timestamp,
                total_xp=r[1],
                total_boss_kills=r[2],
                ehp=r[3],
                ehb=r[4],
                raw_data=raw_json
            )
            db.add(snapshot)
            db.flush() # Flush to get snapshot.id
            
            # Create sub-records
            try:
                data = json.loads(raw_json)
                # Skills
                skills = data.get('data', {}).get('skills', {})
                for s_name, s_data in skills.items():
                    db.add(SkillSnapshot(
                        snapshot_id=snapshot.id,
                        skill_name=s_name,
                        xp=s_data.get('experience', 0),
                        level=s_data.get('level', 1),
                        rank=s_data.get('rank', -1)
                    ))
                
                # Bosses
                bosses = data.get('data', {}).get('bosses', {})
                for b_name, b_data in bosses.items():
                    kills = b_data.get('kills', -1)
                    if kills > 0:
                         db.add(BossSnapshot(
                            snapshot_id=snapshot.id,
                            boss_name=b_name,
                            kills=kills,
                            rank=b_data.get('rank', -1)
                        ))
            except Exception as parse_err:
                 logger.error(f"Failed to parse inner JSON for structure: {parse_err}")

            count += 1
            
        db.commit()
        logger.info(f"Saved {count} WOM snapshots (with detailed stats).")
    except Exception as e:
        logger.error(f"Error saving snapshots: {e}")
    finally:
        db.close()

@timed_operation("WOM Deep Sync")
async def process_wom_snapshots_deep(group_id, members_list):
    """Deep Sync: Fetches full snapshot history for all members (Incremental)."""
    logger.info(f"Starting SMART DEEP SYNC for {len(members_list)} members...")
    db = SessionLocal()
    
    # helper to find latest timestamp for a user (Thread Safe)
    def get_latest_timestamp_thread_safe(username):
        db_local = SessionLocal()
        try:
            stmt = select(WOMSnapshot.timestamp).where(WOMSnapshot.username == username.lower()).order_by(desc(WOMSnapshot.timestamp)).limit(1)
            result = db_local.execute(stmt).scalar()
            return result
        finally:
            db_local.close()

    # We fetch ALL snapshots for each user
    async def fetch_history(username):
        try:
            # Smart Sync: Get latest DB entry (Non-blocking)
            latest_ts = await asyncio.to_thread(get_latest_timestamp_thread_safe, username)
            start_date_str = None
            
            if latest_ts:
                # Add 1 second to avoid fetching the exact same snapshot again
                # Convert to ISO format for API
                # WOM API expects ISO string. We need to be careful with TZ.
                # Assuming DB stores naive UTC or aware UTC.
                # Let's ensure it's treated as UTC.
                ts = latest_ts.replace(tzinfo=timezone.utc) if latest_ts.tzinfo is None else latest_ts
                # Add 1 sec buffer
                ts = ts + timedelta(seconds=1)
                start_date_str = ts.isoformat()
                start_date_str = ts.isoformat()
                # logger.info(f"[{username}] Incremental fetch from {start_date_str}")
            else:
                logger.info(f"[{username}] FULL HISTORY FETCH (No previous data found)")
            
            snaps = await wom_client.get_player_snapshots(username, start_date=start_date_str)
            return (username, snaps)
        except Exception as e:
            logger.error(f"Failed deep fetch for {username}: {e}")
            return (username, [])

    tasks = [fetch_history(m['username']) for m in members_list]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} Users"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task_id = progress.add_task("[magenta]Deep Syncing...", total=len(tasks))
        
        for f in asyncio.as_completed(tasks):
            username, snaps = await f
            if snaps:
                # 1. Fetch existing timestamps to prevent duplicates
                existing_ts = await asyncio.to_thread(get_all_timestamps_thread_safe, username)
                
                count_added = 0
                for s in snaps:
                    ts_str = s.get('createdAt')
                    try:
                        # Parse TS
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        
                        # DEDUPLICATION CHECK
                        # Ensure TS is aware UTC for comparison
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                            
                        if ts in existing_ts:
                            continue # Skip duplicate
                            
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
                        db.add(snap)
                        count_added += 1
                    except Exception as e:
                        logger.error(f"Error duplicate/parse snapshot for {username}: {e}")
                        continue
                
                # Batch Commit Logic Loop handled outside or implicitly by session accumulation
                # We just let the loop continue.
            
            # Commit every 10 users
            
            # Commit every 10 users
            if progress.tasks[task_id].completed % 10 == 0:
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Batch DB Commit failed: {e}")
                    db.rollback()
            
            progress.advance(task_id)

    # Final Commit
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Final DB Commit failed: {e}")
            
    db.close()
    logger.info("Smart Deep Sync Complete.")

def get_all_timestamps_thread_safe(username):
    db_local = SessionLocal()
    try:
        stmt = select(WOMSnapshot.timestamp).where(WOMSnapshot.username == username.lower())
        results = db_local.execute(stmt).scalars().all()
        # Return as set of aware UTC datetimes (assuming DB stores naive UTC)
        # We need to standardize on UTC aware for comparison
        cleaned = set()
        for t in results:
             if t:
                # Force UTC aware
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                cleaned.add(t)
        return cleaned
    finally:
        db_local.close()

@timed_operation("Name Change Detection")
async def check_name_changes(members_data):
    """Detects if users have changed names since last run."""
    logger.info("Checking for name changes...")
    db = SessionLocal()
    try:
        # Get last run users
        # Helper: get distinct usernames from latest snapshots
        # This is a bit heavy, maybe just check distinct usernames in `wom_records` (legacy table)
        # or just previous Fetch? 
        # Let's use `wom_snapshots` distinct ordered by time.
        
        # Simple heuristic: users in DB but NOT in `members_data` are "Missing".
        # users in `members_data` but NOT in DB are "New".
        # We map Missing -> New via WOM API.
        
        current_names = {normalize_user_string(m['username']) for m in members_data}
        
        # Get all users seen in last 7 days from DB
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stmt = select(WOMSnapshot.username).where(WOMSnapshot.timestamp >= cutoff).distinct()
        recent_db_users = set(db.execute(stmt).scalars().all())
        
        missing = recent_db_users - current_names
        
        if not missing:
            logger.info("No missing users detected.")
            return

        logger.info(f"Analyzing {len(missing)} missing users...")
        
        for old_name in missing:
            # Check WOM API
            try:
                changes = await wom_client.search_name_changes(old_name)
                target = None
                for c in changes:
                    if c.get('oldName', '').lower() == old_name:
                        target = c
                        break
                
                if target:
                    new_name = target.get('newName')
                    logger.info(f"Name Change Detected: {old_name} -> {new_name}")
                    
                    if normalize_user_string(new_name) in recent_db_users:
                        logger.info(f"Merging history: {new_name} already exists in DB. Consolidating records...")
                        # Proceed with update instead of skipping
                        
                    # Perform Rename in DB
                    # 1. Update Snapshots
                    db.query(WOMSnapshot).filter(WOMSnapshot.username == old_name).update({WOMSnapshot.username: new_name})
                    # 2. Update Discord Messages
                    # This is harder because author_name might not match exactly or requires fuzzy logic.
                    # We'll skip Discord rename for safety unless we are sure.
                    # existing `main.py` did: db.execute('UPDATE discord_messages ...')
                    # Let's assume we do it.
                    # But we don't have a direct model query easily without circular deps or messy logic.
                    # We'll do raw SQL for update to keep it simple or use model update.
                    from database.models import DiscordMessage
                    db.query(DiscordMessage).filter(DiscordMessage.author_name == old_name).update({DiscordMessage.author_name: new_name})
                    
                    db.commit()
                    logger.info("Database Updated.")
                    
            except Exception as e:
                logger.error(f"Error checking {old_name}: {e}")
                
    finally:
        db.close()

async def run_harvest(close_client=True):
    init_db()
    logger.info("--- Starting Harvest ---")
    
    # 1. Update Group
    if Config.WOM_GROUP_ID and Config.WOM_GROUP_SECRET:
        try:
            logger.info("Triggering WOM Group Update...")
            await wom_client.update_group(Config.WOM_GROUP_ID, Config.WOM_GROUP_SECRET)
            await wom_client.update_group(Config.WOM_GROUP_ID, Config.WOM_GROUP_SECRET)
            
            wait_time = Config.WOM_UPDATE_WAIT
            if not Config.TEST_MODE:
                logger.info(f"Waiting {wait_time}s for WOM propagation...")
                await asyncio.sleep(wait_time) 
        except Exception as e:
            logger.error(f"Group update failed: {e}")

    # 2. Get Members
    members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
    if Config.TEST_MODE:
        members = members[:Config.TEST_LIMIT]
        logger.info(f"[Test Mode] Limited to {len(members)} members.")

    # 3. Name Changes
    await check_name_changes(members)

    # 4. Parallel Fetch
    logger.info("Starting Parallel Fetch (Discord + WOM)...")
    
    # Discord
    # We fetch ALL messages from CUSTOM_START_DATE if DB is empty, or incremental.
    # The Service handles logic? No, the service handles *a* fetch.
    # Logic: get latest DB time, start from there.
    
    db = SessionLocal()
    # Get latest Discord msg time
    # Equivalent to SELECT MAX(created_at)
    from database.models import DiscordMessage
    latest = db.query(DiscordMessage.created_at).order_by(desc(DiscordMessage.created_at)).first()
    db.close()
    
    # Determine incremental start date
    start_dt = datetime.fromisoformat(Config.CUSTOM_START_DATE).replace(tzinfo=timezone.utc)
    if latest and latest[0]:
        start_dt = latest[0].replace(tzinfo=timezone.utc)

    # Safety cap: do not look back further than Config.DAYS_LOOKBACK
    cap_dt = datetime.now(timezone.utc) - timedelta(days=Config.DAYS_LOOKBACK)
    if start_dt < cap_dt:
        logger.info(f"Capping Discord fetch window to last {Config.DAYS_LOOKBACK} days (from {start_dt.date()} -> {cap_dt.date()})")
        start_dt = cap_dt

    discord_task = asyncio.create_task(discord_service.fetch(start_date=start_dt))
    
    if Config.WOM_DEEP_SCAN:
        logger.warning(">>> DEEP SCAN ENABLED: Fetching full history for all members. This may take a while. <<<")
        wom_task = asyncio.create_task(process_wom_snapshots_deep(Config.WOM_GROUP_ID, members))
    else:
        wom_task = asyncio.create_task(process_wom_snapshots(Config.WOM_GROUP_ID, members))
    
    await discord_task
    await wom_task
    
    logger.info("--- Harvest Complete ---")
    if close_client:
        await wom_client.close()

if __name__ == "__main__":
    asyncio.run(run_harvest(True))
