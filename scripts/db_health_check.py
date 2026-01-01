import sqlite3
import sys
import os
from core.config import Config

def check():
    if not os.path.exists(Config.DB_FILE):
        print(f"FAIL: {Config.DB_FILE} not found.")
        return False
    
    try:
        conn = sqlite3.connect(Config.DB_FILE)
        cursor = conn.cursor()
        
        # Check Tables
        tables = ['clan_members', 'wom_snapshots', 'discord_messages']
        for t in tables:
            try:
                cursor.execute(f"SELECT count(*) FROM {t}")
                count = cursor.fetchone()[0]
                print(f"Table '{t}': {count} rows")
                if count == 0:
                    print(f"FAIL: Table '{t}' is empty.")
                    return False
            except sqlite3.OperationalError as e:
                print(f"FAIL: Table '{t}' error: {e}")
                return False
        
        # Check User Data (partymarty94)
        cursor.execute("SELECT count(*) FROM discord_messages WHERE author_name='partymarty94' COLLATE NOCASE")
        pm_msgs = cursor.fetchone()[0]
        print(f"partymarty94 messages: {pm_msgs}")
        if pm_msgs == 0:
            print("FAIL: No messages for key user partymarty94")
            return False
            
        print("PASS: DB Health Check OK")
        return True
    except Exception as e:
        print(f"FAIL: Exception: {e}")
        return False
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    success = check()
    sys.exit(0 if success else 1)
