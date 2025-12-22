import asyncio
import sqlite3
import os
import sys
from datetime import datetime
sys.path.append(os.getcwd())

from core.config import Config
from data.queries import Queries

async def test_optimization():
    print("Testing Local-First Optimization...")
    db_path = Config.DB_FILE
    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Get Members
    print("Fetching members from DB...")
    cursor.execute("SELECT username FROM clan_members")
    members = cursor.fetchall()
    print(f"Found {len(members)} members.")

    skipped_count = 0
    checks = 0
    
    # 2. Check for today's snapshot
    print("Checking for existing snapshots (Validation)...")
    for row in members:
        uname = row[0]
        checks += 1
        try:
            cursor.execute(Queries.CHECK_TODAY_SNAPSHOT, (uname,))
            if cursor.fetchone():
                skipped_count += 1
                # print(f"  [Skipped] {uname}")
        except Exception as e:
            print(f"Error checking {uname}: {e}")

    conn.close()
    
    print("-" * 30)
    print(f"Total Members: {len(members)}")
    print(f"Checked: {checks}")
    print(f"Skipped (Optimized): {skipped_count}")
    print(f"Need Update: {len(members) - skipped_count}")

    if skipped_count > 0:
        print("SUCCESS: Logic found existing snapshots.")
    else:
        print("NOTE: No snapshots found for today. (Expected if fresh start)")

if __name__ == "__main__":
    asyncio.run(test_optimization())
