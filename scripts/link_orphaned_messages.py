import sqlite3
from core.usernames import UsernameNormalizer
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("Linker")

DB_PATH = "clan_data.db"

def fix_systemic_links():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Get all current Clan Members (ID -> Normalized Name)
    cursor.execute("SELECT id, username FROM clan_members")
    members = cursor.fetchall()
    
    # Map: normalized_username -> member_id
    # We use strict normalization for the key
    member_map = {}
    for mid, name in members:
        norm = UsernameNormalizer.normalize(name)
        if norm:
            member_map[norm] = mid
            
    print(f"Loaded {len(member_map)} members for matching.")
    
    # 2. Get all ORPHANED messages (user_id IS NULL)
    # Group by author_name to be efficient
    cursor.execute("SELECT author_name, COUNT(*) FROM discord_messages WHERE user_id IS NULL GROUP BY author_name")
    orphans = cursor.fetchall()
    
    print(f"Found {len(orphans)} unique orphaned author names.")
    
    match_count = 0
    msg_count = 0
    
    for author_name, count in orphans:
        if not author_name: continue
        
        # Normalize the Discord Author Name
        norm_author = UsernameNormalizer.normalize(author_name)
        
        # Try to find a match in clan_members
        if norm_author in member_map:
            target_id = member_map[norm_author]
            print(f"🔗 Linking '{author_name}' ({count} msgs) -> Member ID {target_id} (Norm: '{norm_author}')")
            
            # Execute Update
            cursor.execute("UPDATE discord_messages SET user_id = ? WHERE author_name = ? AND user_id IS NULL", (target_id, author_name))
            match_count += 1
            msg_count += count
        else:
            # Optional: Log failures to see who is truly unknown
            # print(f"  Unknown: '{author_name}' (Norm: '{norm_author}')")
            pass

    conn.commit()
    conn.close()
    
    print(f"\n✅ Systemic Fix Complete.")
    print(f"  - Matched Authors: {match_count}")
    print(f"  - Total Messages Linked: {msg_count}")

if __name__ == "__main__":
    fix_systemic_links()
