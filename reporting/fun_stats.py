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
from database.models import WOMSnapshot, DiscordMessage
from core.utils import normalize_user_string

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("FunStats")

async def get_snapshots_bulk(db, usernames: List[str], target_date: datetime) -> Dict[str, WOMSnapshot]:
    """Fetched latest snapshot on or before target_date."""
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

def get_total_messages(db) -> Dict[str, int]:
    """Counts ALL messages per user in the DB."""
    stmt = (
        select(
            func.lower(DiscordMessage.author_name).label("name"), 
            func.count(DiscordMessage.id).label("count")
        )
        .group_by(func.lower(DiscordMessage.author_name))
    )
    results = db.execute(stmt).all()
    
    # Normalize
    counts = {}
    for row in results:
        norm = normalize_user_string(row.name)
        counts[norm] = counts.get(norm, 0) + row.count
        
    return counts

def analyze_raids(bosses: Dict) -> Tuple[str, int, float]:
    """ Returns (BestRaidName, KillsInThatRaid, PercentageOfTotalRaidKills) """
    # Raid keys
    cox_keys = ['chambers_of_xeric', 'chambers_of_xeric_challenge_mode']
    tob_keys = ['theatre_of_blood', 'theatre_of_blood_hard_mode']
    toa_keys = ['tombs_of_amascut', 'tombs_of_amascut_expert']
    
    def sum_keys(keys):
        return sum(bosses.get(k, {}).get('kills', 0) for k in keys if bosses.get(k))

    cox = sum_keys(cox_keys)
    tob = sum_keys(tob_keys)
    toa = sum_keys(toa_keys)
    
    total_raids = cox + tob + toa
    if total_raids == 0:
        return ("None", 0, 0.0)
        
    stats = [("Chambers of Xeric", cox), ("Theatre of Blood", tob), ("Tombs of Amascut", toa)]
    # Find max
    best_raid, kills = max(stats, key=lambda x: x[1])
    
    return (best_raid, kills, kills / total_raids)

async def main():
    db = SessionLocal()
    try:
        logger.info("--- 🎲 CALCULATING CLAN FUN STATS (UPGRADED) 🎲 ---")
        
        # 1. Get List of Users
        stmt_users = select(WOMSnapshot.username).distinct()
        all_users = db.execute(stmt_users).scalars().all()
        logger.info(f"Analyzing {len(all_users)} members...")
        
        # 2. Fetch Data
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        
        # Snapshots
        current_snaps = await get_snapshots_bulk(db, all_users, now)
        old_snaps = await get_snapshots_bulk(db, all_users, week_ago)
        
        # Messages
        msg_counts = get_total_messages(db)
        
        # 3. Process Metrics
        user_stats = []
        
        for u in all_users:
            curr = current_snaps.get(u)
            if not curr: continue
            
            # Message Count
            norm_u = normalize_user_string(u)
            msgs = msg_counts.get(norm_u, 0)
            
            # Boss Kills
            total_boss = curr.total_boss_kills
            
            # XP / EHP Gain 7d
            old = old_snaps.get(u)
            xp_gain = 0
            ehp_gain = 0
            
            if old:
                xp_gain = curr.total_xp - old.total_xp
                ehp_gain = (curr.ehp or 0) - (old.ehp or 0)
            else:
                xp_gain = 0
                ehp_gain = 0
                
            # Raid Spec
            try:
                data = json.loads(curr.raw_data)
                boss_data = data.get('data', {}).get('bosses', {}) or data.get('bosses', {})
                best_raid, raid_kills, raid_ratio = analyze_raids(boss_data)
            except:
                best_raid, raid_kills, raid_ratio = "None", 0, 0.0

            user_stats.append({
                'name': u,
                'msgs': msgs,
                'boss_kills': total_boss,
                'total_xp': curr.total_xp,
                'xp_7d': xp_gain,
                'ehp_gain': ehp_gain,
                'best_raid': best_raid,
                'raid_kills': raid_kills,
                'raid_ratio': raid_ratio
            })
            
        # 4. Determine Winners
        
        # --- The Yap-Star ---
        yappers = [u for u in user_stats if u['msgs'] > 0 or u['boss_kills'] > 0]
        yap_star = max(yappers, key=lambda x: x['msgs'] / max(1, x['boss_kills'])) if yappers else None
        
        # --- The Hitman --- (Min 50 Boss Kills)
        hitmen = [u for u in user_stats if u['boss_kills'] >= 50]
        hitman = min(hitmen, key=lambda x: x['msgs'] / x['boss_kills']) if hitmen else None
        
        # --- The Silent Grinder --- (0 msgs)
        silent_types = [u for u in user_stats if u['msgs'] == 0]
        silent_grinder = max(silent_types, key=lambda x: x['xp_7d']) if silent_types else None
        
        # --- The Specialist --- (Min 50 raid kills)
        specialists = [u for u in user_stats if u['raid_kills'] >= 50]
        specialist = max(specialists, key=lambda x: x['raid_ratio']) if specialists else None
        
        # --- The Efficiency Demon --- (Max EHP Gain)
        # Filter negative gains (wom glitches sometimes)
        ehp_users = [u for u in user_stats if u['ehp_gain'] > 0]
        efficiency_demon = max(ehp_users, key=lambda x: x['ehp_gain']) if ehp_users else None
        
        # --- Rivalry Watch ---
        # Active users only (XP Gain > 0), sorted by Total XP
        active_users = [u for u in user_stats if u['xp_7d'] > 0 and u['total_xp'] > 1_000_000] # Min 1M XP to be relevant
        active_users.sort(key=lambda x: x['total_xp'], reverse=True)
        
        best_rivalry = None
        min_gap_pct = 100.0
        
        for i in range(len(active_users) - 1):
            p1 = active_users[i]
            p2 = active_users[i+1]
            
            gap = p1['total_xp'] - p2['total_xp']
            avg = (p1['total_xp'] + p2['total_xp']) / 2
            if avg == 0: continue
            
            pct = (gap / avg) * 100
             # We want small gap, but high stakes (high XP). 
             # Let's just find the TOP rivalry (highest total XP with gap < 5%)
            if pct < 5.0 and pct < min_gap_pct:
                 best_rivalry = (p1, p2, pct)
                 min_gap_pct = pct
                 # Break early? No, let's find the TIGHTEST gap? 
                 # Actually, "Rivalry at the top" is cooler. 
                 # Let's pick the highest XP pair with < 3% gap.
                 if pct < 3.0:
                     best_rivalry = (p1, p2, pct)
                     break # Found a high ranking close match
        
        # 5. Generate Report
        report = []
        report.append("📢 **WEEKLY CLAN SPOTLIGHT** 📢")
        report.append("---------------------------------")
        
        if yap_star:
            yap_ratio = yap_star['msgs'] / max(1, yap_star['boss_kills'])
            report.append(f"\n🗣️ **THE YAP-STAR**: {yap_star['name'].upper()}")
            report.append(f"   > *Ratio*: {yap_ratio:.2f} Messages per Boss Kill")
            report.append(f"   > Sent {yap_star['msgs']} msgs while slaying only {yap_star['boss_kills']} bosses. Absolute politician.")

        if hitman:
            report.append(f"\n🔫 **THE HITMAN**: {hitman['name'].upper()}")
            report.append(f"   > *Efficiency*: {(hitman['msgs']/hitman['boss_kills']):.4f} Msgs/Kill")
            report.append(f"   > {hitman['boss_kills']} confirmed kills. {hitman['msgs']} words spoken. Strictly business.")
        
        if silent_grinder:
            report.append(f"\n👻 **THE SILENT GRINDER**: {silent_grinder['name'].upper()}")
            report.append(f"   > *Gains*: {silent_grinder['xp_7d']:,} XP gained this week")
            report.append(f"   > Zero messages sent. The grind speaks for itself.")
            
        if specialist:
            spec_pct = specialist['raid_ratio'] * 100
            report.append(f"\n🏰 **THE SPECIALIST**: {specialist['name'].upper()}")
            report.append(f"   > *Obsession*: {specialist['best_raid']} ({spec_pct:.1f}% of raid history)")
            report.append(f"   > Lives in the raid. Probably pays rent there.")

        if efficiency_demon:
            report.append(f"\n📈 **THE EFFICIENCY DEMON**: {efficiency_demon['name'].upper()}")
            report.append(f"   > *Sweat Level*: {efficiency_demon['ehp_gain']:.2f} EHP Gained")
            report.append(f"   > Maximum efficiency. XP waste is a foreign concept.")
            
        if best_rivalry:
            p1, p2, pct = best_rivalry
            # Who gained more?
            chaser = p2 if p2['xp_7d'] > p1['xp_7d'] else p1
            report.append(f"\n⚔️ **RIVALRY WATCH**: {p1['name'].upper()} vs {p2['name'].upper()}")
            report.append(f"   > *Gap*: Only {pct:.2f}% separates these titans!")
            report.append(f"   > {chaser['name'].upper()} is pushing hard with {chaser['xp_7d']:,} XP gained this week.")
            
        final_output = "\n".join(report)
        print(final_output)
        
        # Save to file
        with open("weekly_spotlight.txt", "w", encoding="utf-8") as f:
            f.write(final_output)
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
