
import sqlite3

def inspect():
    with sqlite3.connect("clan_data.db") as conn:
        cursor = conn.cursor()
        
        # List tables
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print("TABLES:", [t[0] for t in tables])
        
        for t in tables:
            table = t[0]
            print(f"\n--- {table} ---")
            cols = cursor.execute(f"PRAGMA table_info({table})").fetchall()
            for c in cols:
                print(f"  {c[1]} ({c[2]})")

if __name__ == "__main__":
    inspect()
