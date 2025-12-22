
import sqlite3
import os

DB_PATH = "clan_data.db"

def check():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} does not exist.")
        return
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print("Running integrity check...")
        res = cursor.execute("PRAGMA integrity_check").fetchone()
        print(f"Integrity Check Result: {res[0]}")
        conn.close()
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    check()
