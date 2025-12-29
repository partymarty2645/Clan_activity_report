import sqlite3

DB_PATH = "clan_data.db"

# Map: Canonical Name -> List of Author Name Patterns or Specific Names
MATRIX = {
    "nevrsolo": ["nevr solo", "nevr purples", "nevrsolo"],
    "theerecter": ["the erecter", "theerecter"],
    "vanvolterii": ["vanvolter ii", "vanvolter", "vanvolterii"],
    "psilocyn": ["psilocyn"],
    "docofmed": ["docofmed"],
    "theforgegod": ["theforgegod"],
    "badglen": ["badglen", "badglen5"],
    "partymarty94": ["partymarty94"],
    "netfllxnchll": ["netfllxnchll"],
    "bmandabking": ["bmandabking"],
    "easyenough": ["easyenough", "easy enough"],
    "eachitandeye": ["eachitandeye"],
    "wonindstink": ["wonindstink"],
    "jakestl314": ["jakestl314", "jake stl 314", "jakestl"],
    "gimmustyyy": ["gimmustyyy", "gim musty", "gim mustyyy"],
    "b0otyband1t": ["b0otyband1t", "booty bandit"],
    "jbwell": ["jbwell", "jb well"],
    "tysonslap": ["tysonslap", "tyson slap"],
    "lilithsdemon": ["lilithsdemon"],
    "samaelilith": ["samaelilith"],
    "mtndck": ["mtndck"],
    "ironmtndck": ["ironmtndck"],
    "golami": ["golami"],
    "epaullet": ["epaullet"],
    "colordeaf": ["colordeaf", "color deaf"],
    "brootha": ["brootha"],
    "dikkedenn": ["dikkedenn", "dikke denn"],
    "kushtikev420": ["kushtikev420"],
    "xterminater": ["xterminater"],
    "p2k": ["p2k", "im p2k", "imp2k"],
    "reagan921": ["reagan921"]
}

def force_merge():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- ☢️ NUCLEAR MERGE INITIATED ☢️ ---")
    
    for good_name, aliases in MATRIX.items():
        print(f"\nProcessing '{good_name}'...")
        
        # 1. Get Target ID
        cursor.execute("SELECT id FROM clan_members WHERE username = ?", (good_name,))
        row = cursor.fetchone()
        if not row:
            print(f"  ❌ good_name '{good_name}' not found! Skipping.")
            continue
        target_id = row[0]
        print(f"  ✅ Target ID: {target_id}")
        
        # 2. Find ALL Bad IDs (ANY ID that isn't Target ID but matches aliases)
        # We search messages first to find IDs linked to these names
        bad_ids = set()
        
        # 2a. Find IDs currently linked to messages with these author names
        for alias in aliases:
            cursor.execute(f"SELECT DISTINCT user_id FROM discord_messages WHERE author_name LIKE ? AND user_id IS NOT NULL", (alias,))
            rows = cursor.fetchall()
            for r in rows:
                if r[0] != target_id:
                    bad_ids.add(r[0])
                    
        # 2b. Find IDs from clan_members (duplicates)
        for alias in aliases:
             # Normalize for search is risky, let's use LIKE
             cursor.execute("SELECT id FROM clan_members WHERE username LIKE ? AND id != ?", (f"%{alias}%", target_id))
             rows = cursor.fetchall()
             for r in rows:
                 bad_ids.add(r[0])

        print(f"  ⚠️ Found {len(bad_ids)} Fragmented IDs: {bad_ids}")
        
        # 3. MERGE IDs
        for bad_id in bad_ids:
            # Move Snapshots
            cursor.execute("UPDATE wom_snapshots SET user_id = ? WHERE user_id = ?", (target_id, bad_id))
            # Move Messages
            cursor.execute("UPDATE discord_messages SET user_id = ? WHERE user_id = ?", (target_id, bad_id))
            msg_count = cursor.rowcount
            if msg_count > 0:
                print(f"    -> Moved {msg_count} messages from ID {bad_id}.")
            
            # Delete Bad Member (if exists)
            cursor.execute("DELETE FROM clan_members WHERE id = ?", (bad_id,))
            
        # 4. LINK ORPHANS (Name Match)
        for alias in aliases:
            cursor.execute("UPDATE discord_messages SET user_id = ? WHERE author_name = ? AND user_id IS NULL", (target_id, alias))
            if cursor.rowcount > 0:
                print(f"    -> Linked {cursor.rowcount} orphans for alias '{alias}'.")
                
    conn.commit()
    conn.close()
    print("\n✅ Nuclear Merge Complete.")

if __name__ == "__main__":
    force_merge()
