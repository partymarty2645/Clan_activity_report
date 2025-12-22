#!/usr/bin/env python3
"""Check why clan_members IDs are not properly populated."""

import sqlite3

conn = sqlite3.connect('clan_data.db')
c = conn.cursor()

print("CLAN MEMBERS ID ANALYSIS")
print("=" * 80)

# Check if IDs are sequential from ROWID assignment
c.execute('SELECT MIN(id), MAX(id), COUNT(*) FROM clan_members WHERE id IS NOT NULL')
min_id, max_id, count = c.fetchone()
print(f"\nID assignment status:")
print(f"  Min ID: {min_id}")
print(f"  Max ID: {max_id}")
print(f"  Count with ID: {count}")

# Check ROWID
c.execute('SELECT COUNT(DISTINCT rowid) FROM clan_members')
rowid_count = c.fetchone()[0]
print(f"  Unique ROWIDs: {rowid_count}")

# Check if the IDs are actually sequential
c.execute('SELECT id FROM clan_members WHERE id IS NOT NULL ORDER BY id LIMIT 20')
ids = [row[0] for row in c.fetchall()]
print(f"\n  First 20 IDs: {ids}")

# Check if all IDs are there
c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NULL')
null_ids = c.fetchone()[0]
print(f"\n  NULL IDs: {null_ids}/404")

# Check actual problem
print("\n" + "=" * 80)
print("PROBLEM DIAGNOSIS:")
print("=" * 80)

if null_ids > 100:
    print("\n❌ Most IDs are NULL - migration didn't work correctly")
    print("\nPossible causes:")
    print("  1. Update statements failed silently")
    print("  2. Clauses didn't match any rows")
    print("  3. Migration ran but data wasn't there")
    
    # Check first member
    c.execute('SELECT rowid, id, username FROM clan_members LIMIT 1')
    rowid, id_val, username = c.fetchone()
    print(f"\nSample member:")
    print(f"  ROWID: {rowid}")
    print(f"  ID: {id_val}")
    print(f"  Username: {username}")
    
    # Try the UPDATE manually
    print("\nTrying manual ID assignment:")
    test_id = rowid + 1  # Since it's 1-indexed
    print(f"  ROWID {rowid} should have ID ~{test_id}")
    
else:
    print("\n✅ IDs appear to be populated correctly")

conn.close()
