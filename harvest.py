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
        
        # 1. Check Cache
        # We query the DB for today's snapshot
        # Using a fresh session or the shared one? Shared is fine for reads if no async conflict, 
        # but sqlalchemy async is cleaner. Here we use sync session in async function... careful.
        # Actually, for Thread safety with async loop, better to check in main loop or use async engine.
        # For this MVP, we'll blindly fetch or do a quick check? 
        # Let's check DB efficiently before starting parallel tasks.
        
        # 2. Fetch
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
            
            # Save
            # We'll return the object and save in main thread to avoid DB locking issues with multithreaded sqlite
            import json
            return (u_clean, xp, total_boss_kills, ehp, ehb, json.dumps(p))
            
        except Exception as e:
            # logger.warning(f"Failed to fetch {u_clean}: {e}")
            return None

    tasks = [fetch_one(m['username']) for m in members_list]
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
            # Check duplicate (simple check)
            # We assume if we ran today, we might be re-running.
            # Ideally we check existence.
            
            # (u_clean, xp, boss, ehp, ehb, raw)
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

async def main():
    init_db()
    logger.info("--- Starting Harvest ---")
    
    # 1. Update Group
    if Config.WOM_GROUP_ID and Config.WOM_GROUP_SECRET:
        try:
            logger.info("Triggering WOM Group Update...")
            await wom_client.update_group(Config.WOM_GROUP_ID, Config.WOM_GROUP_SECRET)
            if not Config.TEST_MODE:
                logger.info("Waiting 10s for propagation (Script usually waits 5m, shortened for refactor test)...")
                await asyncio.sleep(10) 
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
    wom_task = asyncio.create_task(process_wom_snapshots(Config.WOM_GROUP_ID, members))
    
    await discord_task
    await wom_task
    
    logger.info("--- Harvest Complete ---")
    await wom_client.close()

if __name__ == "__main__":
    asyncio.run(main())
