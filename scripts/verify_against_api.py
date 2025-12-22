import sqlite3
import requests
import json
import time

DB_PATH = "clan_data.db"
API_BASE = "https://api.wiseoldman.net/v2/players"

CHECKS = [
    ("rlood", "dagannoth_rex"),
    ("dip an dots", "callisto"),
    ("geordie93", "king_black_dragon"),
    ("vieze kaas", "the_hueycoatl"),
    ("onamorn899", "the_corrupted_gauntlet"),
    ("juwanbukake", "artio"),
    ("p2k", "barrows_chests"),
    ("wizzard6612", "vorkath"),
    ("joke smolnts", "callisto"),
    ("netfllxnchll", "vetion"),
    ("lapis lzuli", "thermonuclear_smoke_devil"),
    ("brootha", "sarachnis"),
    ("b1ack noir", "general_graardor"),
    ("roadking6", "scurrius")
]

def get_api_data(username):
    try:
        url = f"{API_BASE}/{username}"
        resp = requests.get(url, headers={'User-Agent': 'ClanStatsVerification/1.0'})
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return None
        else:
            print(f"API Error {resp.status_code} for {username}")
            return None
    except Exception as e:
        print(f"Request failed for {username}: {e}")
        return None

def verify_live():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"{'Username':<15} | {'Boss':<25} | {'DB Kills':<8} | {'API Kills':<9} | {'Status':<10}")
    print("-" * 80)
    
    with open("api_verification_results.txt", "w", encoding="utf-8") as f:
        header = f"{'Username':<15} | {'Boss':<25} | {'DB Kills':<8} | {'API Kills':<9} | {'Status':<10}\n"
        f.write(header)
        f.write("-" * 80 + "\n")
        
        for user, boss in CHECKS:
            # 1. Get DB Value (Latest)
            db_kills = "N/A"
            try:
                cursor.execute('''
                    SELECT b.kills 
                    FROM boss_snapshots b 
                    JOIN wom_snapshots w ON b.snapshot_id = w.id 
                    WHERE w.username = ? AND b.boss_name = ?
                    ORDER BY w.timestamp DESC LIMIT 1
                ''', (user, boss))
                row = cursor.fetchone()
                if row:
                    db_kills = row['kills']
            except:
                pass

            # 2. Get API Value
            api_kills = "Err"
            api_data = get_api_data(user)
            
            if api_data:
                # WOM API structure: latestSnapshot -> data -> bosses -> [boss_name] -> kills
                # Boss keys in API might differ slightly (e.g. no underscrores? or camelCase?)
                # Actually WOM API v2 usually uses snak_case for keys in the json output corresponding to metrics.
                # Let's check 'latestSnapshot' -> 'data' -> 'bosses' -> 'boss_name' -> 'kills'
                try:
                    boss_data = api_data.get('latestSnapshot', {}).get('data', {}).get('bosses', {}).get(boss)
                    if boss_data:
                        api_kills = boss_data.get('kills', -1)
                    else:
                        api_kills = "Not Fnd"
                except Exception as e:
                    api_kills = f"Parse Err"
            else:
                api_kills = "404/Err"
            
            # 3. Compare
            status = "MATCH"
            if str(db_kills) != str(api_kills):
                status = "MISMATCH"
                if api_kills == "Not Fnd" and db_kills == 0:
                     status = "MATCH (0)" # Assuming not found means 0 or unranked
            
            line = f"{user:<15} | {boss:<25} | {str(db_kills):<8} | {str(api_kills):<9} | {status:<10}"
            print(line)
            f.write(line + "\n")
            
            time.sleep(0.5) # Rate limit courtesy using wait if needed, though 14 requests is small.

    conn.close()
    print("\nResults written to api_verification_results.txt")

if __name__ == "__main__":
    verify_live()
