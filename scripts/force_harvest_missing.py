import sys
import os
import asyncio
import json
import datetime
from datetime import timezone

sys.path.append(os.getcwd())
try:
    from services.factory import ServiceFactory
    from services.wom import WOMClient
    from database.connector import SessionLocal
    from core.usernames import UsernameNormalizer
    from data.queries import Queries
    import sqlite3
except ImportError:
    # Fallback for direct run
    pass

DB_PATH = "clan_data.db"

async def force_harvest():
    targets = ['cervixthumpr', 'sulkypeen']
    
    print(f"Force Harvesting: {targets}")
    
    wom = await ServiceFactory.get_wom_client()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    ts_now_iso = datetime.datetime.now(timezone.utc).isoformat()
    
    for user in targets:
        print(f"Updating {user}...")
        try:
            # 1. Update Player (Force new snapshot)
            data = await wom.update_player(user)
            if not data:
                print(f"❌ Failed to UPDATE {user} (None returned)")
                continue
            
            print(f"✅ Update Successful for {user}")
            
            # 2. Extract Snapshot
            snap = data.get('latestSnapshot')
            if not snap:
                # Sometimes update returns the snapshot directly or nested?
                # The update response IS a snapshot usually? No, it returns Player Details usually.
                # Let's check full keys
                print(f" Keys in response: {list(data.keys())}")
                if 'id' in data and 'createdAt' in data and 'data' in data:
                     # It MIGHT be the snapshot itself
                     snap = data
                     print("  (Response appears to be a snapshot)")
                else: 
                     print(f"❌ No snapshot in data for {user}")
                     continue
                
            u_clean = UsernameNormalizer.normalize(user)
            
            # Resolve ID manually since we are using raw sqlite
            cursor.execute("SELECT id FROM clan_members WHERE username = ?", (u_clean,))
            row = cursor.fetchone()
            member_id = row[0] if row else None
            
            if not member_id:
                print(f"⚠️ Member ID not found for {u_clean}, inserting NULL id")

            # 3. Save
            snap_data = snap.get('data', {})
            skills = snap_data.get('skills', {})
            bosses = snap_data.get('bosses', {})
            
            xp = skills.get('overall', {}).get('experience', 0)
            ehp = data.get('ehp', 0)
            ehb = data.get('ehb', 0)
            total_boss = sum(b.get('kills', 0) for b in bosses.values() if b.get('kills', 0) > 0)
            raw_json = json.dumps(snap)
            
            try:
                cursor.execute(Queries.INSERT_SNAPSHOT, (u_clean, ts_now_iso, xp, total_boss, ehp, ehb, raw_json, member_id))
                snap_id = cursor.lastrowid
                print(f"  -> Saved Snapshot ID: {snap_id} (XP: {xp})")
                
                # Bosses
                boss_rows = []
                for b_name, b_val in bosses.items():
                    kills = b_val.get('kills', -1)
                    rank = b_val.get('rank', -1)
                    if kills > -1:
                        boss_rows.append((snap_id, b_name, kills, rank))
                        
                if boss_rows:
                    cursor.executemany(Queries.INSERT_BOSS_SNAPSHOT, boss_rows)
                    print(f"  -> Saved {len(boss_rows)} boss records")
                    
            except Exception as e:
                print(f"❌ DB Error saving {user}: {e}")
                
        except Exception as e:
            print(f"❌ API Error fetching {user}: {e}")
            
    conn.commit()
    conn.close()
    await ServiceFactory.cleanup()

if __name__ == "__main__":
    asyncio.run(force_harvest())
