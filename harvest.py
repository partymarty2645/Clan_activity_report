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
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from core.config import Config
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

async def process_wom_snapshots(group_id, members_list):
    """Fetches full player details for all members and saves snapshots."""
    logger.info(f"Processing WOM snapshots for {len(members_list)} members...")
    
    db = SessionLocal()
    
    # Pre-fetch today's snapshots to skip
    today_prefix = datetime.now().isoformat()[:10]
    
    async def fetch_one(username):
        u_clean = username.lower()
        
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
    today_date = datetime.now().date()
    # Find users who already have a snapshot today
    from sqlalchemy import func
    stmt = select(WOMSnapshot.username).where(func.date(WOMSnapshot.timestamp) == str(today_date))
    already_done = set(db.execute(stmt).scalars().all())
    
    target_members = []
    for m in members_list:
        if m['username'].lower() in already_done:
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
        timestamp = datetime.now()
        for r in results:
            snapshot = WOMSnapshot(
                username=r[0],
                timestamp=timestamp,
                total_xp=r[1],
                total_boss_kills=r[2],
                ehp=r[3],
                ehb=r[4],
                raw_data=r[5]
            )
            db.add(snapshot)
            count += 1
        db.commit()
        logger.info(f"Saved {count} WOM snapshots.")
    except Exception as e:
        logger.error(f"Error saving snapshots: {e}")
    finally:
        db.close()

async def process_wom_snapshots_deep(group_id, members_list):
    """Deep Sync: Fetches full snapshot history for all members."""
    logger.info(f"Starting DEEP SYNC for {len(members_list)} members...")
    db = SessionLocal()
    
    # We fetch ALL snapshots for each user
    async def fetch_history(username):
        try:
            snaps = await wom_client.get_player_snapshots(username)
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
                # Deduplicate and Save
                # This could be thousands of records.
                # Optimization: Get existing timestamps for this user.
                
                # Careful with TZ. WOM snaps are ISO8601 string.
                # DB stores datetime.
                # We'll parse the incoming ts.
                
                new_records = []
                for s in snaps:
                    ts_str = s.get('createdAt')
                    # Parse logic
                    try:
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        # Make naive if relying on naive DB or aware if aware.
                        # Usually DB connector handles conversion if column is DateTime
                        # But comparing:
                        # Let's just try to insert? No, excessive unique checks.
                        # Simple check:
                        
                        # We blindly insert? Only if we handle integrity errors.
                        # Or check existance first.
                        # This is "Deep Sync", arguably rare.
                        # Let's check DB efficiently?
                        # Maybe simply checking latest snapshot isn't enough.
                        
                        # Implementation Plan for Deep Sync:
                        # 1. Just save everything? No, dupes.
                        # 2. Check if (username, timestamp) exists.
                        # We'll rely on a basic SELECT count or just timestamp check.
                        
                        # Check existance query
                        # stmt = select(1).where(WOMSnapshot.username==username, WOMSnapshot.timestamp==ts)
                        # We'll assume if we haven't seen this TS, save it.
                        
                        # Optimization: Fetch all TS for user in one query
                        # existing_ts = set(db.scalars(select(WOMSnapshot.timestamp).where(WOMSnapshot.username==username)).all())
                        # This works.
                        pass
                    except:
                        continue
                        
                # Actually, implementing full deep sync logic is complex in one go.
                # Let's simplify:
                # Just fetch and invoke backfill logic!
                # We essentially have `backfill_missing_history` in REPORT.PY.
                # We are in HARVEST. 
                # Let's replicate strict insert logic here.
                
                import json
                
                # Get existing TS for user
                stmt = select(WOMSnapshot.timestamp).where(WOMSnapshot.username == username.lower())
                existing_ts_raw = db.execute(stmt).scalars().all()
                # Create a set of ISO strings or datetimes for rough comparison
                # Note: Existing DB TS might be microsecond precise or not.
                # WOM API usually is.
                # Let's map existing to set of timestamps.
                existing_set = {t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t for t in existing_ts_raw}

                count_added = 0
                for s in snaps:
                    ts_str = s.get('createdAt')
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    
                    # Fuzzy match check (same second)
                    is_dupe = False
                    for ex in existing_set:
                         if abs((ex - ts).total_seconds()) < 1:
                             is_dupe = True
                             break
                    
                    if is_dupe:
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
                    db.add(snap)
                    count_added += 1
                
                if count_added > 0:
                    db.commit()
            
            progress.advance(task_id)
            
    db.close()
    logger.info("Deep Sync Complete.")

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
        
        current_names = {m['username'].lower() for m in members_data}
        
        # Get all users seen in last 7 days from DB
        cutoff = datetime.now() - timedelta(days=7)
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
                    
                    if new_name.lower() in recent_db_users:
                        logger.warning(f"Skipping merge: {new_name} already exists in DB.")
                        continue
                        
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
            if not Config.TEST_MODE:
                if Config.WOM_SHORT_UPDATE_DELAY:
                    logger.info("Waiting 10s for propagation (Short Wait Enabled)...")
                    await asyncio.sleep(10)
                else:
                    logger.info("Waiting 5 minutes for propagation (Full Wait)...")
                    await asyncio.sleep(300) 
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
    
    start_dt = datetime.fromisoformat(Config.CUSTOM_START_DATE).replace(tzinfo=timezone.utc)
    if latest and latest[0]:
        start_dt = latest[0].replace(tzinfo=timezone.utc)
    
    
    discord_task = asyncio.create_task(discord_service.fetch(start_date=start_dt))
    
    if Config.WOM_DEEP_SCAN:
        logger.warning(">>> DEEP SCAN ENABLED: Fetching full history for all members. This may take a while. <<<")
        wom_task = asyncio.create_task(process_wom_snapshots_deep(Config.WOM_GROUP_ID, members))
    else:
        wom_task = asyncio.create_task(process_wom_snapshots(Config.WOM_GROUP_ID, members))
    
    await discord_task
    
    await discord_task
    await wom_task
    
    logger.info("--- Harvest Complete ---")
    if close_client:
        await wom_client.close()

if __name__ == "__main__":
    asyncio.run(run_harvest(True))
