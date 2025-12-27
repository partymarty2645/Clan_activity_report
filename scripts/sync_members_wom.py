import sys
import os
import requests
import csv
import io
import logging

sys.path.append(os.getcwd())
from core.config import Config
from database.connector import SessionLocal
from database.models import ClanMember
from core.usernames import UsernameNormalizer

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("SyncMembers")

def sync_members():
    # 1. Fetch JSON from WOM (More reliable than CSV guess)
    group_id = Config.WOM_GROUP_ID
    url = f"https://api.wiseoldman.net/v2/groups/{group_id}"
    logger.info(f"Fetching Member List (JSON) from: {url}")
    
    wom_members = set()
    
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        # Parse JSON
        # data['memberships'] -> list of { player: { username... } }
        for m in data.get('memberships', []):
            p = m.get('player', {})
            if p.get('username'):
                wom_members.add(UsernameNormalizer.normalize(p['username']))
                
        logger.info(f"WOM Total Members (via JSON): {len(wom_members)}")
        
    except Exception as e:
        logger.error(f"Failed to fetch WOM Data: {e}")
        return

    # 3. Load Local DB Members

    # 3. Load Local DB Members
    session = SessionLocal()
    local_members = session.query(ClanMember).all()
    local_map = {UsernameNormalizer.normalize(m.username): m.username for m in local_members}
    
    logger.info(f"Local Total Members: {len(local_map)}")
    
    # 4. Find Differences
    # In Local but NOT in WOM = STALE/LEFT
    stale_users = set(local_map.keys()) - wom_members
    
    # In WOM but NOT in Local = NEW/MISSING from Discord?
    new_users = wom_members - set(local_map.keys())
    
    print(f"\n--- Analysis ---")
    print(f"Stale Users (In Local, Not in WOM): {len(stale_users)}")
    print(f"New Users (In WOM, Not in Local): {len(new_users)}")
    
    # 5. Check the 22 Zero-Boss Users specifically
    # We recall them from previous task or just logic: "Local users with 0 kills usually match Stale"
    
    if stale_users:
        print("\nExamples of Stale Users (Likely cause of 0 stats):")
        sorted_stale = sorted([local_map[k] for k in stale_users])
        for x in sorted_stale[:20]:
            print(f" - {x}")
            
    if new_users:
        print(f"\nNew users found in WOM: {len(new_users)} (These might be recent joins not yet synced via Discord)")

if __name__ == "__main__":
    sync_members()
