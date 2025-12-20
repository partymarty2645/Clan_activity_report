import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from sqlalchemy import select, func, and_

# Adjust path to import core modules
sys.path.append('.')

from database.connector import SessionLocal
from database.models import WOMSnapshot

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("UpgradeResearch")

async def get_snapshots_bulk(db, usernames: List[str], target_date: datetime) -> Dict[str, WOMSnapshot]:
    subq = (
        select(WOMSnapshot.username, func.max(WOMSnapshot.timestamp).label("max_ts"))
        .where(
            WOMSnapshot.username.in_(usernames),
            WOMSnapshot.timestamp <= target_date
        )
        .group_by(WOMSnapshot.username)
        .subquery()
    )
    
    stmt = (
        select(WOMSnapshot)
        .join(subq, and_(
            WOMSnapshot.username == subq.c.username,
            WOMSnapshot.timestamp == subq.c.max_ts
        ))
    )
    results = db.execute(stmt).scalars().all()
    return {r.username: r for r in results}

async def research():
    db = SessionLocal()
    try:
        logger.info("--- RESEARCHING UPGRADES ---")
        
        stmt_users = select(WOMSnapshot.username).distinct()
        all_users = db.execute(stmt_users).scalars().all()
        
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        
        current_snaps = await get_snapshots_bulk(db, all_users, now)
        old_snaps = await get_snapshots_bulk(db, all_users, week_ago)
        
        # 1. CHECK FOR RIVALRIES
        # Criteria: Users within 5% of each other's Total XP
        # And both active (gained XP in last 7d)
        
        active_users = []
        for u in all_users:
            curr = current_snaps.get(u)
            old = old_snaps.get(u)
            if curr and old:
                gain = curr.total_xp - old.total_xp
                if gain > 10000: # Significant gain
                    active_users.append({
                        'name': u,
                        'total_xp': curr.total_xp,
                        'gain': gain
                    })
        
        # Sort by total xp
        active_users.sort(key=lambda x: x['total_xp'], reverse=True)
        
        rivalries = []
        for i in range(len(active_users) - 1):
            p1 = active_users[i]
            p2 = active_users[i+1]
            
            # Check gap percentage
            gap = p1['total_xp'] - p2['total_xp']
            avg_xp = (p1['total_xp'] + p2['total_xp']) / 2
            gap_pct = (gap / avg_xp) * 100
            
            if gap_pct < 5.0: # Less than 5% difference
                rivalries.append(f"{p1['name']} vs {p2['name']} (Gap: {gap_pct:.2f}%)")
                
        logger.info(f"Found {len(rivalries)} potential rivalries.")
        if len(rivalries) > 0:
            logger.info(f"Sample: {rivalries[:3]}")
            
        # 2. CHECK FOR EHP/EHB AVAILABILITY
        # Inspect a few snapshots to see if EHP/EHB fields are populated
        ehp_count = 0
        ehb_count = 0
        for u, snap in current_snaps.items():
            if snap.ehp and snap.ehp > 0:
                ehp_count += 1
            if snap.ehb and snap.ehb > 0:
                ehb_count += 1
                
        logger.info(f"EHP available for {ehp_count}/{len(current_snaps)} users.")
        logger.info(f"EHB available for {ehb_count}/{len(current_snaps)} users.")
        
        if ehp_count > 10:
             logger.info("Upgrade 'Efficiency Demon' is FEASIBLE.")
        else:
             logger.info("Upgrade 'Efficiency Demon' is NOT feasible (insufficient data).")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(research())
