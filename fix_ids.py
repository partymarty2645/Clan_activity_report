#!/usr/bin/env python3
"""Fix clan_members IDs - properly populate for all 404 members."""

import sqlite3

conn = sqlite3.connect('clan_data.db')
c = conn.cursor()

print("FIXING clan_members IDs...")
print("=" * 80)

# Get current state
c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NULL')
null_before = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NOT NULL')
with_id_before = c.fetchone()[0]

print(f"\nBefore:")
print(f"  With ID: {with_id_before}")
print(f"  NULL IDs: {null_before}")

# Fix: Assign IDs based on ROWID (1-indexed)
c.execute("""
    UPDATE clan_members 
    SET id = rowid 
    WHERE id IS NULL
""")

conn.commit()

# Verify
c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NULL')
null_after = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NOT NULL')
with_id_after = c.fetchone()[0]

c.execute('SELECT MIN(id), MAX(id) FROM clan_members')
min_id, max_id = c.fetchone()

print(f"\nAfter:")
print(f"  With ID: {with_id_after}")
print(f"  NULL IDs: {null_after}")
print(f"  ID Range: {min_id} to {max_id}")
print(f"  Total unique IDs: {max_id - min_id + 1 if min_id and max_id else 0}")

# Verify no gaps
c.execute('SELECT COUNT(DISTINCT id) FROM clan_members')
unique_ids = c.fetchone()[0]
print(f"  Unique IDs count: {unique_ids}")

if null_after == 0 and with_id_after == 404:
    print("\n✅ SUCCESS: All 404 members now have IDs!")
else:
    print(f"\n❌ ISSUE: Still {null_after} members without IDs")

conn.close()
