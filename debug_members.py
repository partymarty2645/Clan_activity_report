#!/usr/bin/env python3
"""Debug why we only have 101 members instead of 303."""

import sqlite3

conn = sqlite3.connect('clan_data.db')
c = conn.cursor()

print("DEBUG: WHERE ARE THE 303 MEMBERS?")
print("=" * 80)

# Check what happened
c.execute("SELECT COUNT(*) FROM clan_members")
total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM clan_members WHERE id IS NOT NULL")
with_id = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM clan_members WHERE id IS NULL")
without_id = c.fetchone()[0]

print(f"\nclan_members table:")
print(f"  Total rows: {total}")
print(f"  With ID: {with_id}")
print(f"  Without ID: {without_id}")

# Check when last updated
c.execute("SELECT MAX(last_updated) FROM clan_members")
last_update = c.fetchone()[0]
print(f"\n  Last updated: {last_update}")

# Check unique usernames
c.execute("SELECT COUNT(DISTINCT username) FROM clan_members")
unique = c.fetchone()[0]
print(f"  Unique usernames: {unique}")

# Check WOM snapshots - how many unique users there?
c.execute("""
    SELECT COUNT(DISTINCT username) FROM wom_snapshots
""")
wom_users = c.fetchone()[0]
print(f"\nWOM snapshots unique usernames: {wom_users}")

# Check if we have historical data for inactive members
c.execute("""
    SELECT COUNT(DISTINCT ws.username) 
    FROM wom_snapshots ws
    WHERE ws.username NOT IN (SELECT username FROM clan_members)
""")
inactive = c.fetchone()[0]
print(f"Members in WOM history but NOT in clan_members: {inactive}")

# List some of these inactive members
c.execute("""
    SELECT DISTINCT ws.username 
    FROM wom_snapshots ws
    WHERE ws.username NOT IN (SELECT username FROM clan_members)
    LIMIT 20
""")

print(f"\nSample inactive members (found in WOM data but not in current clan_members):")
for row in c.fetchall():
    print(f"  - {row[0]}")

conn.close()
