import sqlite3
from core.usernames import UsernameNormalizer

DB_PATH = "clan_data.db"

# Target Map: { "Bad/Discord Name" : "Good/WOM Name" }
# We want to find the ID of the "Good Phone" and merge everything into it.
REMAPS = {
    "nevr solo": "nevrsolo",
    "the erecter": "theerecter",
    "vanvolter": "vanvolterii",
    "vanvolter ii": "vanvolterii",
    "vanvolterii": "vanvolterii", # specialized handling
    "mr batgang": "mrbatgang"
}

def fix_links():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for bad_name, good_name in REMAPS.items():
        print(f"\nProcessing: '{bad_name}' -> '{good_name}'")
        
        # 1. Find Target ID (The "Good" one)
        cursor.execute("SELECT id FROM clan_members WHERE username = ?", (good_name,))
        row = cursor.fetchone()
        if not row:
            print(f"  ❌ Target '{good_name}' not found in DB! Skipping.")
            continue
        
        target_id = row[0]
        print(f"  ✅ Target ID for '{good_name}': {target_id}")
        
        # 2. Find "Bad" Member ID (if exists) -> Merge it
        # We search by name (normalized or raw)
        cursor.execute("SELECT id FROM clan_members WHERE username = ? AND id != ?", (bad_name, target_id))
        bad_rows = cursor.fetchall()
        
        for bad_r in bad_rows:
            old_id = bad_r[0]
            print(f"  ⚠️ Found Duplicate Member ID {old_id} for '{bad_name}'. Merging...")
            
            # Move Snapshots
            cursor.execute("UPDATE wom_snapshots SET user_id = ? WHERE user_id = ?", (target_id, old_id))
            print(f"    - Moved {cursor.rowcount} snapshots.")
            
            # Move Messages
            cursor.execute("UPDATE discord_messages SET user_id = ? WHERE user_id = ?", (target_id, old_id))
            print(f"    - Moved {cursor.rowcount} messages.")
            
            # Delete Original
            cursor.execute("DELETE FROM clan_members WHERE id = ?", (old_id,))
            print(f"    - Deleted member {old_id}.")
            
        # 3. Fix Unlinked Messages (Author Name match)
        # Search for messages with this 'bad_name' but NO user_id
        # We use LIKE for flexibility? No, strict first.
        
        # Check by strict name
        cursor.execute("UPDATE discord_messages SET user_id = ? WHERE author_name = ? AND user_id IS NULL", (target_id, bad_name))
        if cursor.rowcount > 0:
            print(f"  🔗 Linked {cursor.rowcount} orphaned messages (Exact Match: '{bad_name}').")
            
        # Check by normalized name (if bad_name isn't already normalized)
        norm_bad = UsernameNormalizer.normalize(bad_name)
        if norm_bad != bad_name:
             cursor.execute("UPDATE discord_messages SET user_id = ? WHERE author_name = ? AND user_id IS NULL", (target_id, norm_bad))
             if cursor.rowcount > 0:
                print(f"  🔗 Linked {cursor.rowcount} orphaned messages (Norm Match: '{norm_bad}').")

        # Fuzzy Check (Contains) - specialized for the specific inputs
        cursor.execute(f"UPDATE discord_messages SET user_id = ? WHERE author_name LIKE ? AND user_id IS NULL", (target_id, f"%{bad_name}%"))
        if cursor.rowcount > 0:
             print(f"  🔗 Linked {cursor.rowcount} orphaned messages (LIKE Match: '%{bad_name}%').")
             
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_links()
