import asyncio
import logging
import argparse
import sys
from datetime import datetime, timezone

from sqlalchemy import select, and_, func
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from core.config import Config
from services.wom import wom_client
from database.connector import SessionLocal
from database.models import WOMSnapshot

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Backfill")

async def backfill(limit=None):
    logger.info("--- Starting Backfill ---")
    
    # 1. Get Members
    logger.info(f"Fetching group members from WOM (Group ID: {Config.WOM_GROUP_ID})...")
    members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
    logger.info(f"found {len(members)} members.")
    
    # Apply limit
    if limit:
        members = members[:limit]
        logger.info(f"Limiting backfill to first {limit} members.")

    db = SessionLocal()
    
    stats = {'processed': 0, 'added': 0, 'skipped': 0, 'errors': 0}

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeRemainingColumn(),
            console=Console()
        ) as progress:
            task_id = progress.add_task("[cyan]Backfilling Snapshots...", total=len(members))
            
            for m in members:
                username = m['username']
                progress.update(task_id, description=f"[cyan]Backfilling {username}...")
                
                try:
                    # Smart Skip: Check if we already have data
                    start_date_limit = datetime(2025, 2, 14, tzinfo=timezone.utc)
                    search_start = "2025-01-01T00:00:00.000Z" # Fetch slightly more to be safe
                    
                    min_ts_stmt = select(func.min(WOMSnapshot.timestamp)).where(WOMSnapshot.username == username.lower())
                    min_ts = db.execute(min_ts_stmt).scalar()
                    
                    if min_ts:
                         # Ensure min_ts is aware
                        if min_ts.tzinfo is None:
                            min_ts = min_ts.replace(tzinfo=timezone.utc)
                            
                        if min_ts <= start_date_limit:
                            progress.advance(task_id)
                            stats['skipped'] += 1
                            # logger.info(f"Skipping {username} (Already has data from {min_ts})")
                            continue

                    # Fetch Snapshots
                    snapshots = await wom_client.get_player_snapshots(username, start_date=search_start)
                    
                    if not snapshots:
                        progress.advance(task_id)
                        stats['processed'] += 1
                        continue

                    # Bulk check existing
                    # Get all timestamps for this user in DB
                    existing_stm = select(WOMSnapshot.timestamp).where(WOMSnapshot.username == username.lower())
                    existing_ts = set(db.execute(existing_stm).scalars().all())
                    
                    new_snapshots = []
                    for s in snapshots:
                        ts_str = s.get('createdAt')
                        if not ts_str: continue
                        
                        # Parse TS
                        try:
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        except:
                            continue
                            
                        # Check exist (naive match)
                        # DB stores as naive or aware? SQLite usually naive text but models.py says DateTime.
                        # We compare aware to aware or naive to naive.
                        # Let's assume DB is naive UTC or matches input.
                        # Best way for duplicate check is strict equality? 
                        # Or checking if we have a snapshot at this exact second.
                        
                        # Timestamp check logic:
                        # Converting to naive UTC for consistent comparison if DB is naive
                        ts_naive = ts.astimezone(timezone.utc).replace(tzinfo=None)
                        
                        if ts_naive in existing_ts or ts in existing_ts:
                            stats['skipped'] += 1
                            continue

                        # Prepare Object
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
                            raw_data="" # Save space, don't store full JSON for backfill unless needed
                        )
                        new_snapshots.append(snap)
                    
                    if new_snapshots:
                        db.add_all(new_snapshots)
                        db.commit()
                        stats['added'] += len(new_snapshots)
                    
                except Exception as e:
                    logger.error(f"Error backfilling {username}: {e}")
                    stats['errors'] += 1
                    
                progress.advance(task_id)
                stats['processed'] += 1

    finally:
        db.close()
        await wom_client.close()

    logger.info("--- Backfill Complete ---")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Added Snapshots: {stats['added']}")
    logger.info(f"Skipped (Existing): {stats['skipped']}")
    logger.info(f"Errors: {stats['errors']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Limit number of users to process')
    args = parser.parse_args()
    
    asyncio.run(backfill(limit=args.limit))
