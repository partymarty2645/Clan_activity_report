import sqlite3
import os
import time
import sys

DB_PATH = "clan_data.db"
JOURNAL_PATH = "clan_data.db-journal"

def recover():
    print("starting recovery...")
    
    if os.path.exists(JOURNAL_PATH):
        print(f"found journal file: {os.path.getsize(JOURNAL_PATH) / 1024 / 1024:.2f} MB")
    else:
        print("no journal file found. database might be clean.")

    try:
        # connect triggers rollback of the journal
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print("connected to database (rollback should be complete)")
        
        # verify journal is gone/empty
        if os.path.exists(JOURNAL_PATH):
            size = os.path.getsize(JOURNAL_PATH)
            if size > 0:
                print(f"warning: journal file still exists and is {size} bytes")
            else:
                print("journal file is empty.")
        else:
            print("journal file is gone.")
            
        print("running vacuum to clean up...")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("VACUUM")
        print("vacuum complete.")
        
        conn.close()
        print("recovery successful.")
        
    except Exception as e:
        print(f"recovery failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    recover()
