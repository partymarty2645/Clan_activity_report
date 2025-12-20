import asyncio
import sys
import os

# Adjust path to allow imports from root when run as script
sys.path.append(os.getcwd())

import argparse
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_
import statistics

from core.config import Config
from services.wom import wom_client
from database.connector import SessionLocal
from database.models import WOMSnapshot, DiscordMessage

# Logging
logging.basicConfig(level=logging.ERROR, format='%(message)s')
logger = logging.getLogger("Enforcer")

# Roles
OFFICER_ROLES = ['owner', 'deputy_owner', 'zenyte', 'dragonstone', 'saviour', 'onyx']

async def get_discord_counts(days: int):
    """Returns {username: count} for last N days."""
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
    """Returns {username: {'xp': int, 'boss': int}} for last N days."""
    db = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    gains = {}
    
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
                has_activity = (end.timestamp - start.timestamp).total_seconds() > 3600
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

async def get_clan_stats(days=30):
    print(f"Fetching Clan Data ({days}d)...")
    members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
    if not members:
        print("Failed to fetch members.")
        return []

    usernames = [m['username'].lower() for m in members]
    role_map = {m['username'].lower(): m['role'] for m in members}
    join_map = {m['username'].lower(): m['joined_at'] for m in members}
    
    discord_data = await get_discord_counts(days)
    wom_data = await get_wom_gains(usernames, days)
    
    stats = []
    for u in usernames:
        s = {
            'username': u,
            'role': role_map.get(u, 'member'),
            'joined_at': join_map.get(u),
            'msgs': discord_data.get(u, 0),
            'xp': wom_data.get(u, {}).get('xp', 0),
            'boss': wom_data.get(u, {}).get('boss', 0)
        }
        stats.append(s)
    return stats

def run_officer_audit(stats, output_file=None):
    out = []
    def log(m):
        print(m)
        out.append(str(m))
        
    log("\n" + "="*50)
    log("      👮 OFFICER PERFORMANCE AUDIT (30d) 👮")
    log("="*50)
    
    # Calc Averages (All members)
    msgs_vals = [s['msgs'] for s in stats]
    xp_vals = [s['xp'] for s in stats]
    
    avg_msgs = statistics.mean(msgs_vals) if msgs_vals else 0
    med_msgs = statistics.median(msgs_vals) if msgs_vals else 0
    avg_xp = statistics.mean(xp_vals) if xp_vals else 0
    
    log(f"CLAN AVERAGE: {avg_msgs:.1f} msgs | {avg_xp:,.0f} XP")
    log(f"CLAN MEDIAN:  {med_msgs:.1f} msgs")
    log("-" * 50)
    log(f"{'OFFICER':<20} | {'ROLE':<12} | {'MSGS':<8} | {'XP GAIN':<15} | {'STATUS'}")
    log("-" * 50)
    
    officers = [s for s in stats if s['role'] in OFFICER_ROLES]
    officers.sort(key=lambda x: x['msgs'], reverse=True)
    
    for o in officers:
        status = "✅"
        # Flag if below AVERAGE messages OR very low XP
        if o['msgs'] < avg_msgs and o['xp'] < 1000000:
            status = "⚠️ Slacking"
        if o['msgs'] == 0:
            status = "🚨 AWOL"
            
        log(f"{o['username']:<20} | {o['role']:<12} | {o['msgs']:<8} | {o['xp']:<15,.0f} | {status}")
        
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out))
            print(f"Officer Audit saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save officer audit: {e}")

def run_purge_generator(stats, output_file=None):
    out = []
    def log(m):
        print(m)
        out.append(str(m))
        
    log("\n" + "="*50)
    log("      💀 PURGE CANDIDATES (Dead Accounts) 💀")
    log("="*50)
    log("CRITERIA: Joined > 30 days ago AND 0 Messages (30d) AND < 10k XP (30d)")
    log("-" * 50)
    
    candidates = []
    now = datetime.now(timezone.utc)
    
    for s in stats:
        # Check join date
        joined_str = s['joined_at']
        if not joined_str: continue
        
        try:
            # WOM format often: 2021-01-01T00:00:00.000Z
            jt = datetime.fromisoformat(joined_str.replace("Z", "+00:00"))
            if (now - jt).days < 30:
                continue # Protected (New Joiner)
        except:
            continue
            
        if s['msgs'] == 0 and s['xp'] < 10000:
            candidates.append(s)
            
    candidates.sort(key=lambda x: x['xp'])
    
    log(f"{'USERNAME':<20} | {'ROLE':<12} | {'XP (30d)':<10} | {'BOSS'}")
    log("-" * 50)
    
    if not candidates:
        log("No purge candidates found! Clan is healthy.")
    else:
        for c in candidates:
            log(f"{c['username']:<20} | {c['role']:<12} | {c['xp']:<10,} | {c['boss']}")
            
    log("-" * 50)
    log(f"Total Candidates: {len(candidates)}")
    
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out))
            print(f"Purge List saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save purge list: {e}")

async def run_enforcer_suite():
    """Runs all enforcer tools and saves reports."""
    stats = await get_clan_stats(30)
    if not stats: 
        logger.error("Skipping Enforcer Suite (No data)")
        return
        
    run_officer_audit(stats, output_file="officer_audit.txt")
    run_purge_generator(stats, output_file="purge_list.txt")

async def main():
    parser = argparse.ArgumentParser(description="Clan Enforcer Toolkit")
    parser.add_argument("--audit", action="store_true", help="Run Officer Audit")
    parser.add_argument("--purge", action="store_true", help="Run Purge Generator")
    parser.add_argument("--all", action="store_true", help="Run Complete Suite (for pipeline)")
    args = parser.parse_args()
    
    if args.all:
        await run_enforcer_suite()
    else:
        # Default behavior if specific flags used
        stats = await get_clan_stats(30)
        if not stats: return
        
        if args.audit:
            run_officer_audit(stats)
        if args.purge:
            run_purge_generator(stats)
            
    await wom_client.close()

if __name__ == "__main__":
    asyncio.run(main())
