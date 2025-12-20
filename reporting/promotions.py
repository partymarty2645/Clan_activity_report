import asyncio
import sys
import os

# Adjust path to allow imports from root when run as script
sys.path.append(os.getcwd())

import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

from services.wom import wom_client
from database.connector import SessionLocal
from database.models import WOMSnapshot

# Configure Logging
logging.basicConfig(level=logging.ERROR) # Quiet most logs
logger = logging.getLogger("PromotionReport")
logger.setLevel(logging.INFO)

DB_PATH = 'e:/Clan_activity_report/clan_data.db'
ZAMORAKIAN_ALIASES = ['zamorakian', 'zenyte', 'dragonstone', 'administrator'] # Fallback ranks
LEADERSHIP_ROLES = ['owner', 'deputy_owner', 'administrator', 'moderator', 'advisor']

async def get_role_map(group_id) -> Dict[str, str]:
    """Fetches current members from API to get accurate roles."""
    print("Fetching live role data from WOM...")
    members = await wom_client.get_group_members(group_id)
    role_map = {}
    for m in members:
        if m['role']:
            role_map[m['username'].lower()] = m['role'].lower()
    return role_map

def get_recent_metrics(days=7) -> Dict[str, Dict]:
    """Calculates XP gains and gets latest boss kills from DB."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Time window
    now_utc = datetime.now(timezone.utc)
    cutoff_7d = now_utc - timedelta(days=7)
    cutoff_30d = now_utc - timedelta(days=30)
    
    # 1. Get Messages (30d)
    print("Analyzing Discord activity...")
    cursor.execute("""
        SELECT lower(author_name) as name, count(*) as count 
        FROM discord_messages 
        WHERE created_at >= ? 
        GROUP BY lower(author_name)
    """, (cutoff_30d.isoformat(),))
    msg_map_30d = {row['name']: row['count'] for row in cursor.fetchall()}
    
    # 2. Get Snapshots (Latest & 7d ago)
    print("Analyzing XP and Boss data...")
    # Fetch latest snapshot for every user
    cursor.execute("""
        SELECT username, total_xp, raw_data 
        FROM wom_snapshots 
        WHERE (username, timestamp) IN (
            SELECT username, MAX(timestamp) 
            FROM wom_snapshots 
            GROUP BY username
        )
    """)
    latest_snaps = cursor.fetchall()
    
    # Fetch snapshot closest to 7d ago
    cursor.execute("""
        SELECT username, total_xp 
        FROM wom_snapshots 
        WHERE timestamp >= ? 
        GROUP BY username 
        HAVING MIN(timestamp)
    """, (cutoff_7d.isoformat(),))
    past_snaps = {row['username']: row['total_xp'] for row in cursor.fetchall()}
    
    metrics = {}
    
    for row in latest_snaps:
        user = row['username']
        cur_xp = row['total_xp']
        past_xp = past_snaps.get(user, 0) # Default to 0 if new
        
        # Calculate Gain
        xp_gain_7d = cur_xp - past_xp if past_xp > 0 else 0 
        
        # Parse Bosses (CoX, ToB, ToA)
        try:
            data = json.loads(row['raw_data'])
            # Handle different JSON structures depending on endpoint source (group vs player)
            # data structure from harvest is usually player details
            api_data = data.get('data', data) # fallback
            bosses = api_data.get('bosses', {})
            
            cox = bosses.get('chambers_of_xeric', {}).get('kills', 0)
            tob = bosses.get('theatre_of_blood', {}).get('kills', 0)
            toa = bosses.get('tombs_of_amascut', {}).get('kills', 0)
            
            # Handle -1 (unranked)
            cox = max(0, cox)
            tob = max(0, tob)
            toa = max(0, toa)
            
            total_raids = cox + tob + toa
        except Exception:
            total_raids = 0
            
        metrics[user] = {
            'xp_gain_7d': xp_gain_7d,
            'msgs_30d': msg_map_30d.get(user, 0),
            'total_raids': total_raids
        }
        
    conn.close()
    return metrics

def generate_report(role_map, metrics):
    print("\nProcessing Promotion Logic...")
    
    recommendations = []
    
    # --- Logic 1: High-Velocity Prospectors ---
    # Find Average XP of 'Zamorakian' (or aliases)
    zam_xp_gains = []
    target_rank_name = "Zamorakian"
    
    for user, role in role_map.items():
        if role in ZAMORAKIAN_ALIASES:
            if user in metrics:
                zam_xp_gains.append(metrics[user]['xp_gain_7d'])
    
    if not zam_xp_gains:
        # Fallback to general member average if no Zamorakians found
        avg_zam_xp = 0
        limit_msg = "(No Zamorakians found, logic skipped)"
    else:
        avg_zam_xp = sum(zam_xp_gains) / len(zam_xp_gains)
        limit_msg = f"(> {avg_zam_xp:,.0f} XP)"

    print(f"Benchmark: {target_rank_name} Avg 7d XP = {avg_zam_xp:,.0f}")
    
    prospectors = [u for u, r in role_map.items() if r == 'prospector']
    for user in prospectors:
        data = metrics.get(user)
        if data and data['xp_gain_7d'] > avg_zam_xp and avg_zam_xp > 0:
            recommendations.append({
                'user': user,
                'rank': 'prospector',
                'reason': f"High Velocity: {data['xp_gain_7d']:,.0f} XP {limit_msg}"
            })

    # --- Logic 2: Social Pillars ---
    # Top 10% Messages 30d, Non-Leadership
    all_msgs = [m['msgs_30d'] for m in metrics.values() if m['msgs_30d'] > 0]
    if all_msgs:
        all_msgs.sort(reverse=True)
        top_10_cutoff_index = int(len(all_msgs) * 0.1)
        # Ensure at least 1 person if list is small, but index 0 is top
        cutoff_val = all_msgs[top_10_cutoff_index] if top_10_cutoff_index < len(all_msgs) else all_msgs[0]
        
        print(f"Benchmark: Top 10% Msg Threshold = {cutoff_val}")
        
        for user, data in metrics.items():
            role = role_map.get(user, 'unknown')
            if role not in LEADERSHIP_ROLES and data['msgs_30d'] >= cutoff_val:
                # Avoid duplicate if already recommended? No, can be multiple reasons.
                # But let's check duplicates later.
                recommendations.append({
                    'user': user,
                    'rank': role,
                    'reason': f"Social Pillar: {data['msgs_30d']} msgs (Top 10%)"
                })

    # --- Logic 3: The Carry Potential ---
    # Low Rank (Guest, Prospector, Member, etc.) with High Raids
    # Strategy: Exclude known High Ranks to capture all custom low roles
    HIGH_RANKS = ['owner', 'deputy_owner', 'administrator', 'moderator', 'advisor', 'zenyte', 'dragonstone', 'zamorakian', 'saviour']
    
    # Defined Carry Threshold
    raid_counts = [m['total_raids'] for m in metrics.values() if m['total_raids'] > 0]
    if raid_counts:
        raid_counts.sort(reverse=True)
        # Top 15% threshold for "High"
        raid_threshold = raid_counts[int(len(raid_counts) * 0.15)]
        if raid_threshold < 50: raid_threshold = 50 # Minimum floor
        
        print(f"Benchmark: Carry Raid Threshold = {raid_threshold}")
        
        for user, data in metrics.items():
            role = role_map.get(user, 'unknown')
            # Check if role is NOT in high ranks (fuzzy match)
            is_high_rank = any(hr in role for hr in HIGH_RANKS)
            
            if not is_high_rank and data['total_raids'] >= raid_threshold:
                recommendations.append({
                    'user': user,
                    'rank': role,
                    'reason': f"Carry Potential: {data['total_raids']} Raids"
                })

    return recommendations

def print_markdown_report(recommendations):
    print("\n" + "="*40)
    print("PROMOTION RECOMMENDATION REPORT")
    print("="*40)
    
    if not recommendations:
        print("No promotions recommended at this time.")
        return

    # Group by User to combine reasons
    grouped = {}
    for r in recommendations:
        u = r['user']
        if u not in grouped:
            grouped[u] = {'rank': r['rank'], 'reasons': []}
        grouped[u]['reasons'].append(r['reason'])
    
    # Sort by Rank priority? Or just Name? Let's Sort by Name.
    sorted_users = sorted(grouped.items())
    
    print(f"{'User':<20} | {'Current Rank':<15} | {'Reason for Recommendation'}")
    print("-" * 80)
    
    for user, data in sorted_users:
        reasons = "; ".join(data['reasons'])
        print(f"{user:<20} | {data['rank']:<15} | {reasons}")
    print("-" * 80)

async def main():
    from core.config import Config
    
    if not Config.WOM_GROUP_ID:
        print("Error: WOM_GROUP_ID not set in environment or config.")
        return

    role_map = await get_role_map(Config.WOM_GROUP_ID)
    metrics = get_recent_metrics()
    recommendations = generate_report(role_map, metrics)
    print_markdown_report(recommendations)
    await wom_client.close()

if __name__ == "__main__":
    asyncio.run(main())
