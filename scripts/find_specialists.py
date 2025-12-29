import sqlite3
import collections

DB_PATH = "clan_data.db"

def analyze():
    print("Connecting to DB...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # query raw data
    print("Fetching raw data...")
    cursor.execute("""
        SELECT cm.username, ws.user_id, ws.timestamp, bs.boss_name, bs.kills
        FROM boss_snapshots bs
        JOIN wom_snapshots ws ON bs.snapshot_id = ws.id
        JOIN clan_members cm ON ws.user_id = cm.id
    """)
    rows = cursor.fetchall()
    conn.close()
    print(f"Fetched {len(rows)} rows.")

    # 1. Filter for Latest Snapshot per User
    latest_snaps = {} # user_id -> timestamp
    user_names = {} # user_id -> username
    
    # First pass: find max timestamp
    for r in rows:
        username, uid, ts, boss, kills = r
        if uid not in latest_snaps or ts > latest_snaps[uid]:
            latest_snaps[uid] = ts
            user_names[uid] = username
            
    # Second pass: Collect data for latest timestamp only
    user_data = {} # uid -> {total: 0, bosses: {}}
    
    for r in rows:
        username, uid, ts, boss, kills = r
        if ts == latest_snaps[uid]:
            if uid not in user_data:
                user_data[uid] = {'total': 0, 'bosses': {}}
            
            # Update total
            # Note: total_boss_kills column exists in wom_snapshots but we can calc it here to be safe
            # Actually summing kills here is accurate for the snapshot
            user_data[uid]['bosses'][boss] = kills
            
    # Calculate totals
    for uid in user_data:
        total = sum(user_data[uid]['bosses'].values())
        user_data[uid]['total'] = total

    # Analyze
    print("\n--- 🎯 ONE-TRICK PONIES (80%+ One Boss, >1000 KC) ---")
    for uid, data in user_data.items():
        total = data['total']
        if total < 1000: continue
        
        username = user_names[uid]
        for boss, kills in data['bosses'].items():
            ratio = kills / total
            if ratio > 0.8:
                print(f"User: {username} | Boss: {boss} ({kills}) | Total: {total} | Ratio: {ratio:.1%}")

    print("\n--- 💀 THE MASOCHISTS (Nightmare/Corp/Nex > 200 KC) ---")
    TEDIOUS = ['corporeal_beast', 'phosani_nightmare', 'the_nightmare', 'nex']
    # Sort masochists
    masochists = []
    
    for uid, data in user_data.items():
        username = user_names[uid]
        for boss, kills in data['bosses'].items():
            if boss in TEDIOUS and kills > 200:
                masochists.append((username, boss, kills))
                
    masochists.sort(key=lambda x: x[2], reverse=True)
    for m in masochists[:10]:
         print(f"User: {m[0]} | Boss: {m[1]} | Kills: {m[2]}")

if __name__ == "__main__":
    analyze()
