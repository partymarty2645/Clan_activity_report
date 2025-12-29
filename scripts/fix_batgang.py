import sqlite3

DB_PATH = "clan_data.db"

def fix_orphans():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Move Messages from 131 -> 6359
    old_id = 131
    new_id = 6359
    
    print(f"Moving messages from ID {old_id} to {new_id}...")
    cursor.execute(f"UPDATE discord_messages SET user_id = {new_id} WHERE user_id = {old_id}")
    count = cursor.rowcount
    
    conn.commit()
    print(f"Fixed {count} messages.")
    conn.close()

if __name__ == "__main__":
    fix_orphans()
