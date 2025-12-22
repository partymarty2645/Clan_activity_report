import sqlite3

DB_PATH = "clan_data.db"

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

def verify():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    with open("verification_results.txt", "w", encoding="utf-8") as f:
        f.write(f"{'Username':<15} | {'Boss':<30} | {'Kills':<6} | {'Timestamp':<25}\n")
        f.write("-" * 80 + "\n")
        
        for user, boss in CHECKS:
            try:
                cursor.execute('''
                    SELECT w.username, b.boss_name, b.kills, w.timestamp 
                    FROM boss_snapshots b 
                    JOIN wom_snapshots w ON b.snapshot_id = w.id 
                    WHERE w.username = ? AND b.boss_name = ?
                    ORDER BY w.timestamp ASC
                ''', (user, boss))
                
                rows = cursor.fetchall()
                if not rows:
                    f.write(f"{user:<15} | {boss:<30} | {'N/A':<6} | No Records Found\n")
                    continue

                first = rows[0]
                last = rows[-1]
                
                f.write(f"{first['username']:<15} | {first['boss_name']:<30} | {first['kills']:<6} | {first['timestamp']}\n")
                if len(rows) > 1:
                    f.write(f"{last['username']:<15} | {last['boss_name']:<30} | {last['kills']:<6} | {last['timestamp']} (Latest)\n")
                f.write("-" * 40 + "\n")
                
            except Exception as e:
                f.write(f"Error checking {user}: {e}\n")

    conn.close()
    print("Verification written to verification_results.txt")

if __name__ == "__main__":
    verify()
