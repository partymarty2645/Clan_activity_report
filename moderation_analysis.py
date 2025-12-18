import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_

from core.config import Config
from services.wom import wom_client
from database.connector import SessionLocal
from database.models import WOMSnapshot, DiscordMessage

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Moderation")

# CONSTANTS
TIER_1_ROLES = ['owner', 'deputy_owner', 'zenyte', 'dragonstone', 'saviour']
TIER_3_ROLES = ['prospector']

async def get_discord_counts(days: int):
    """Returns a dict {username: count} for messages in the last N days."""
    db = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    try:
        stmt = (
            select(DiscordMessage.author_name, func.count(DiscordMessage.id))
            .where(DiscordMessage.created_at >= cutoff)
            .group_by(DiscordMessage.author_name)
        )
        results = db.execute(stmt).all()
        return {r[0].lower(): r[1] for r in results if r[0]}
    finally:
        db.close()

async def get_wom_gains(usernames: list, days: int):
    """
    Returns dict {username: {'xp': int, 'boss': int}} for gains in last N days.
    Calculates gain = (Latest Snapshot - Earliest Snapshot in period).
    """
    db = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    gains = {}
    
    # We can do this efficiently by getting the first snapshot after cutoff and the latest snapshot for each user.
    # For simplicity in this analysis script, let's just fetch all snapshots >= cutoff and process in python.
    # Optimization: Use SQL for min/max per user.
    
    try:
        # Get Latest
        subq_max = (
            select(WOMSnapshot.username, func.max(WOMSnapshot.timestamp).label("max_ts"))
            .group_by(WOMSnapshot.username)
            .subquery()
        )
        stmt_latest = (
            select(WOMSnapshot)
            .join(subq_max, and_(WOMSnapshot.username == subq_max.c.username, WOMSnapshot.timestamp == subq_max.c.max_ts))
            .where(WOMSnapshot.username.in_(usernames))
        )
        latest_snaps = {s.username: s for s in db.execute(stmt_latest).scalars().all()}
        
        # Get Earliest (>= cutoff)
        subq_min = (
            select(WOMSnapshot.username, func.min(WOMSnapshot.timestamp).label("min_ts"))
            .where(WOMSnapshot.timestamp >= cutoff)
            .group_by(WOMSnapshot.username)
            .subquery()
        )
        stmt_earliest = (
            select(WOMSnapshot)
            .join(subq_min, and_(WOMSnapshot.username == subq_min.c.username, WOMSnapshot.timestamp == subq_min.c.min_ts))
            .where(WOMSnapshot.username.in_(usernames))
        )
        earliest_snaps = {s.username: s for s in db.execute(stmt_earliest).scalars().all()}
        
        for u in usernames:
            start = earliest_snaps.get(u)
            end = latest_snaps.get(u)
            
            if start and end:
                has_activity = (end.timestamp - start.timestamp).total_seconds() > 3600 # significant time passed
                if has_activity:
                    xp_gain = end.total_xp - start.total_xp
                    boss_gain = end.total_boss_kills - start.total_boss_kills
                    gains[u] = {'xp': max(0, xp_gain), 'boss': max(0, boss_gain)}
                else:
                    gains[u] = {'xp': 0, 'boss': 0}
            else:
                gains[u] = {'xp': 0, 'boss': 0}
                
        return gains
    finally:
        db.close()

async def analyze_moderation(output_file=None):
    logger.info("Starting Moderation Analysis...")
    out_lines = []
    
    def log(msg):
        print(msg)
        out_lines.append(str(msg))

    log("Fetching Clan Members...")
    members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
    if not members:
        log("Failed to fetch members.")
        return

    usernames = [m['username'].lower() for m in members]
    role_map = {m['username'].lower(): m['role'] for m in members}
    
    log("Fetching Activity Data...")
    discord_7d = await get_discord_counts(7)
    discord_30d = await get_discord_counts(30)
    wom_7d = await get_wom_gains(usernames, 7)
    
    # --- Analysis ---
    
    leadership_slump = []
    churn_risk = []
    silent_recruits = []
    
    for u in usernames:
        role = role_map.get(u, 'member').lower()
        msg_7d = discord_7d.get(u, 0)
        msg_30d = discord_30d.get(u, 0)
        xp_7d = wom_7d.get(u, {}).get('xp', 0)
        boss_7d = wom_7d.get(u, {}).get('boss', 0)
        
        # 1. Leadership Slump
        if role in TIER_1_ROLES:
            if xp_7d == 0 and boss_7d == 0 and msg_7d == 0:
                leadership_slump.append({'name': u, 'role': role})
                
        # 2. Churn Risk
        if msg_30d > 100 and msg_7d < 10:
             churn_risk.append({'name': u, 'role': role, 'msg_30d': msg_30d, 'msg_7d': msg_7d})
             
        # 3. Silent Recruit
        if role == 'prospector':
             if msg_7d == 0 and (xp_7d > 0 or boss_7d > 0):
                 silent_recruits.append({'name': u, 'xp': xp_7d, 'boss': boss_7d})

    # --- Output ---
    log("\n" + "="*40)
    log("      🚨 MODERATION ALERT LIST 🚨")
    log("="*40)
    
    log(f"\n[LEADERSHIP SLUMP] - (Tier 1 Inactivity)")
    if leadership_slump:
        for x in leadership_slump:
            log(f"🚨 {x['name']} ({x['role']})")
    else:
        log("  None detected!")

    log(f"\n[CHURN RISK] - (Fading Stars)")
    if churn_risk:
        for x in churn_risk:
            icon = "🚨" if x['msg_7d'] == 0 else "⚠️"
            log(f"{icon} {x['name']} ({x['msg_30d']} msgs -> {x['msg_7d']} in last 7d)")
    else:
        log("  None detected!")

    log(f"\n[SILENT RECRUITS] - (Active Gameplay, No Chat)")
    if silent_recruits:
        for x in silent_recruits:
            log(f"⚠️ {x['name']} (XP: {x['xp']:,}, Boss: {x['boss']}, Msgs: 0)")
    else:
        log("  None detected!")
        
    # We do NOT close the client here if it is shared, but checks here created it?
    # wom_client is a singleton instance. Typically Main pipeline manages connection.
    # But this script runs standalone too.
    # If run from main, main closes. If run standalone, main block closes.
    
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
            logger.info(f"Moderation report saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to write output file: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_moderation("moderation_report.txt"))
    asyncio.run(wom_client.close())
