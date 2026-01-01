import sqlite3
import sys
import os

# Ensure we can import from parent directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config

conn = sqlite3.connect(Config.DB_FILE)
cursor = conn.cursor()

print("=== EXISTING INDEXES ===\n")
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")
for row in cursor.fetchall():
    print(f"{row[0]}:")
    print(f"  {row[1]}\n")

print("\n=== TABLE STRUCTURES ===\n")
for table in ['wom_snapshots', 'discord_messages', 'boss_snapshots', 'clan_members']:
    print(f"\n{table}:")
    cursor.execute(f"PRAGMA table_info({table})")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]})")

conn.close()
