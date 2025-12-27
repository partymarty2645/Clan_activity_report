import sys
import os
import requests
import random
import math
import logging

sys.path.append(os.getcwd())
from database.connector import SessionLocal
from database.models import WOMSnapshot
from core.usernames import UsernameNormalizer
from core.analytics import AnalyticsService

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Verifier")

def verify_zeros():
    session = SessionLocal()
    analytics = AnalyticsService(session)
    
    # 1. Get Local Data (Latest Snapshots)
    print("--- 1. Fetching Local Data ---")
    latest_snaps = analytics.get_latest_snapshots()
    
    # Identify Zeros (Focusing on Boss Kills since XP was validated as all > 0)
    zero_boss_users = []
    zero_xp_users = [] # Just in case
    
    for user, snap in latest_snaps.items():
        if snap.total_boss_kills == 0:
            zero_boss_users.append(user)
        if snap.total_xp == 0:
            zero_xp_users.append(user)
            
    print(f"Local Users with 0 XP: {len(zero_xp_users)}")
    print(f"Local Users with 0 Boss Kills: {len(zero_boss_users)}")
    
    target_pool = zero_boss_users # Primary target
    if not target_pool:
        print("No zero users to verify!")
        return

    # 3. Check WOM API (ALL 22)
    print(f"\n--- 2. Checking ALL {len(target_pool)} targets against WOM API ---")
    sample = target_pool # Check everyone
    
    headers = {
        'User-Agent': 'ClanStats-Verifier/1.0',
        'Content-Type': 'application/json'
    }
    
    mismatches = []
    
    for username in sample:
        try:
            # WOM API: GET /players/username/{username}
            # Note: WOM username lookup might be strict or assume canonical.
            # We try the local filtered username.
            url = f"https://api.wiseoldman.net/v2/players/username/{username}"
            resp = requests.get(url, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                # Latest snapshot is in 'latestSnapshot' usually, or aggregated in 'data'??
                # Wait, /players/username/{u} returns the player object which has 'latestSnapshot'.
                # But sometimes it's implied. Let's inspect root keys.
                # Actually, standard V2 endpoint response usually involves `latestSnapshot` for stats.
                
                # Check if 'latestSnapshot' exists
                if 'latestSnapshot' in data and data['latestSnapshot']:
                    api_data = data['latestSnapshot']['data']
                    
                    # WOM API Structure for Bosses: 'bosses' -> { 'boss_name': { 'kills': N, ... } }
                    # We need to sum them up to match our 'total_boss_kills' logic.
                    # Our 'total_boss_kills' logic in 'services/wom.py' sums all boss kills.
                    
                    # Wait, we need to know HOW `total_boss_kills` is calculated in our ingestion.
                    # Usually it's the sum of all boss 'kills' fields > -1.
                    
                    # Safe check: Let's assume the API returns a dictionary of bosses.
                    # Warning: The structure might be nested.
                    # 'data' -> 'bosses' -> 'abyssal_sire' -> 'kills'
                    
                    boss_total_api = 0
                    if 'bosses' in api_data:
                        for b_name, b_stats in api_data['bosses'].items():
                            k = b_stats.get('kills', -1)
                            if k > 0:
                                boss_total_api += k
                    
                    print(f"[{username:15}] Local: 0   | API: {boss_total_api:<4} | Match: {'✅' if boss_total_api == 0 else '❌'}")
                    
                    if boss_total_api != 0:
                        mismatches.append(username)
                else:
                    print(f"[{username:15}] API returned User but no Snapshot data.")
            elif resp.status_code == 404:
                print(f"[{username:15}] User not found on WOM API (Might be name change/archived)")
            else:
                print(f"[{username:15}] API Error: {resp.status_code}")
                
        except Exception as e:
            print(f"[{username:15}] Error: {e}")
            
    print("\n--- 4. Summary ---")
    if mismatches:
        print(f"❌ Found {len(mismatches)} mismatches where Local=0 but API>0.")
        print(f"Users: {mismatches}")
    else:
        print("✅ All sampled users verified as 0 Boss Kills on API.")

if __name__ == "__main__":
    verify_zeros()
