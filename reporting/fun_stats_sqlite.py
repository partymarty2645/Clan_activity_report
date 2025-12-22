
import sqlite3
import json
import logging
import sys
import datetime
import os
from datetime import timezone, timedelta

# Adjust path if needed
sys.path.append('.')

from core.usernames import UsernameNormalizer
from core.config import Config

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("FunStatsSQLite")

DB_PATH = "clan_data.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_snapshots_bulk(u_list, target_date):
    """
    Fetched latest snapshot ID and metrics on or before target_date for given users.
    Returns {username: {id, timestamp, total_xp, total_boss_kills, ehp}}
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    target_str = target_date.isoformat()
    placeholders = ",".join("?" for _ in u_list)
    query = f'''
        SELECT s.id, s.username, s.timestamp, s.total_xp, s.total_boss_kills, s.ehp
        FROM wom_snapshots s
        INNER JOIN (
            SELECT username, MAX(timestamp) as max_ts
            FROM wom_snapshots
            WHERE timestamp <= ?
            AND username IN ({placeholders})
            GROUP BY username
        ) latest ON s.username = latest.username AND s.timestamp = latest.max_ts
    '''
    
    params = [target_str] + u_list
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = {}
    for r in rows:
        result[r[1]] = {
            'id': r[0],
            'username': r[1],
            'timestamp': r[2],
            'total_xp': r[3],
            'total_boss_kills': r[4],
            'ehp': r[5]
        }
    return result

def get_raid_stats_bulk(snapshot_ids):
    """
    Fetches raid kills for a list of snapshot IDs.
    Returns {snapshot_id: {raid_name: kills}}
    """
    if not snapshot_ids:
        return {}
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    placeholders = ",".join("?" for _ in snapshot_ids)
    # raids we care about for 'The Specialist'
    target_bosses = [
        'chambers_of_xeric', 'chambers_of_xeric_challenge_mode',
        'theatre_of_blood', 'theatre_of_blood_hard_mode',
        'tombs_of_amascut', 'tombs_of_amascut_expert'
    ]
    boss_placeholders = ",".join("?" for _ in target_bosses)
    
    query = f'''
        SELECT snapshot_id, boss_name, kills
        FROM boss_snapshots
        WHERE snapshot_id IN ({placeholders})
        AND boss_name IN ({boss_placeholders})
    '''
    
    params = snapshot_ids + target_bosses
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Organize by snapshot_id
    data = {}
    for r in rows:
        sid, boss, kills = r
        if sid not in data:
            data[sid] = {}
        data[sid][boss] = kills
    return data

def get_total_messages():
    """Counts ALL messages per user (author_name) in the DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Note: Using author_name as fixed in previous step
    cursor.execute('''
        SELECT author_name, COUNT(*)
        FROM discord_messages
        GROUP BY author_name
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    counts = {}
    for r in rows:
        if r[0]:
            norm = UsernameNormalizer.normalize(r[0])
            counts[norm] = counts.get(norm, 0) + r[1]
            
    return counts

def analyze_raids(raid_data):
    """ Returns (BestRaidName, KillsInThatRaid, PercentageOfTotalRaidKills) """
    if not raid_data:
       return ("None", 0, 0.0)

    # Raid keys
    cox_keys = ['chambers_of_xeric', 'chambers_of_xeric_challenge_mode']
    tob_keys = ['theatre_of_blood', 'theatre_of_blood_hard_mode']
    toa_keys = ['tombs_of_amascut', 'tombs_of_amascut_expert']
    
    def sum_keys(keys):
        return sum(raid_data.get(k, 0) for k in keys)

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

def main():
    logger.info("--- 🎲 CALCULATING CLAN FUN STATS (SQLITE) 🎲 ---")
    
    # 1. Get List of Users
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT username FROM wom_snapshots")
    rows = cursor.fetchall()
    all_users = [r[0] for r in rows if r[0]]
    conn.close()
    
    logger.info(f"Analyzing {len(all_users)} members...")
    
    # 2. Fetch Data
    now = datetime.datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    
    # Snapshots
    current_snaps = get_snapshots_bulk(all_users, now)
    old_snaps = get_snapshots_bulk(all_users, week_ago)
    
    # Raid Stats (Bulk Fetch)
    snapshot_ids = [s['id'] for s in current_snaps.values()]
    logger.info(f"Fetching raid stats for {len(snapshot_ids)} snapshots...")
    raid_stats_map = get_raid_stats_bulk(snapshot_ids)
    
    # Messages
    msg_counts = get_total_messages()
    
    # 3. Process Metrics
    user_stats = []
    
    for u in all_users:
        curr = current_snaps.get(u)
        if not curr: continue
        
        # Message Count
        norm_u = normalize_user_string(u)
        msgs = msg_counts.get(norm_u, 0)
        
        # Boss Kills
        total_boss = curr['total_boss_kills']
        
        # XP / EHP Gain 7d
        old = old_snaps.get(u)
        xp_gain = 0
        ehp_gain = 0
        
        if old:
            xp_gain = curr['total_xp'] - old['total_xp']
            ehp_val = curr['ehp'] if curr['ehp'] is not None else 0
            old_ehp = old['ehp'] if old['ehp'] is not None else 0
            ehp_gain = ehp_val - old_ehp
        else:
            xp_gain = 0
            ehp_gain = 0
            
        # Raid Spec
        try:
            raid_data = raid_stats_map.get(curr['id'], {})
            best_raid, raid_kills, raid_ratio = analyze_raids(raid_data)
        except Exception as e:
            # logger.error(f"Error analyzing raids for {u}: {e}")
            best_raid, raid_kills, raid_ratio = "None", 0, 0.0

        user_stats.append({
            'name': u,
            'msgs': msgs,
            'boss_kills': total_boss,
            'total_xp': curr['total_xp'],
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

        if pct < 5.0 and pct < min_gap_pct:
             best_rivalry = (p1, p2, pct)
             min_gap_pct = pct

             if pct < 3.0:
                 best_rivalry = (p1, p2, pct)
                 break 
    
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
        
    # Export to Drive if configured
    drive_path = Config.LOCAL_DRIVE_PATH
    if drive_path and os.path.exists(drive_path):
        import shutil
        try:
             shutil.copy("weekly_spotlight.txt", os.path.join(drive_path, "weekly_spotlight.txt"))
             print(f"Successfully exported weekly_spotlight.txt to {drive_path}")
        except Exception as e:
             print(f"Failed to export to Drive: {e}")
    elif drive_path:
        print(f"Warning: Drive path defined but not found: {drive_path}")

if __name__ == "__main__":
    main()
