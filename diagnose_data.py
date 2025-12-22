#!/usr/bin/env python3
"""Diagnose database data issues."""

import sqlite3

conn = sqlite3.connect('clan_data.db')
c = conn.cursor()

print("DATABASE DIAGNOSIS")
print("=" * 80)

# Check clan_members
c.execute('SELECT COUNT(*) FROM clan_members')
total = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NOT NULL')
with_id = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM clan_members WHERE joined_at IS NOT NULL')
with_joined = c.fetchone()[0]

print(f"\nclan_members table:")
print(f"  Total rows: {total}")
print(f"  With ID: {with_id} ({100*with_id/total:.1f}%)")
print(f"  With joined_at: {with_joined} ({100*with_joined/total:.1f}%)")

# Show members with actual IDs
print(f"\n  Members WITH IDs (first 5):")
c.execute('SELECT username, id, joined_at FROM clan_members WHERE id IS NOT NULL LIMIT 5')
for i, row in enumerate(c.fetchall(), 1):
    print(f"    {i}. {row[0]:<30} id={row[1]} joined={row[2]}")

# Show members without IDs
print(f"\n  Members WITHOUT IDs (first 5):")
c.execute('SELECT username, id, joined_at FROM clan_members WHERE id IS NULL LIMIT 5')
for i, row in enumerate(c.fetchall(), 1):
    print(f"    {i}. {row[0]:<30} id={row[1]} joined={row[2]}")

# Check wom_snapshots
c.execute('SELECT COUNT(*) FROM wom_snapshots')
wom_total = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM wom_snapshots WHERE user_id IS NOT NULL')
wom_with_fk = c.fetchone()[0]

print(f"\nwom_snapshots table:")
print(f"  Total rows: {wom_total}")
print(f"  With user_id FK: {wom_with_fk} ({100*wom_with_fk/wom_total:.1f}%)")

# Check boss_snapshots schema first
c.execute("PRAGMA table_info(boss_snapshots)")
boss_cols = [row[1] for row in c.fetchall()]
print(f"\nboss_snapshots columns: {boss_cols}")

c.execute('SELECT COUNT(*) FROM boss_snapshots')
boss_total = c.fetchone()[0]

if 'kills_count' in boss_cols:
    c.execute('SELECT SUM(CAST(kills_count AS INTEGER)) FROM boss_snapshots')
    result = c.fetchone()
    total_kills = result[0] if result[0] else 0
    avg_kills = total_kills/boss_total if boss_total > 0 else 0
else:
    total_kills = "N/A (column not found)"
    avg_kills = "N/A"

print(f"  Total rows: {boss_total}")
print(f"  Total boss kills: {total_kills}")
print(f"  Average per record: {avg_kills}")

# Check discord_messages
c.execute('SELECT COUNT(*) FROM discord_messages')
discord_total = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM discord_messages WHERE user_id IS NOT NULL')
discord_with_fk = c.fetchone()[0]

print(f"\ndiscord_messages table:")
print(f"  Total rows: {discord_total}")
print(f"  With user_id FK: {discord_with_fk} ({100*discord_with_fk/discord_total:.1f}%)")

print("\n" + "=" * 80)
print("ISSUES SUMMARY:")
print("=" * 80)

issues = []

if with_id < total * 0.9:
    issues.append(f"❌ Only {with_id}/{total} clan_members have IDs populated")

if with_joined < total * 0.9:
    issues.append(f"❌ Only {with_joined}/{total} clan_members have joined_at dates")

if wom_with_fk < wom_total * 0.9:
    issues.append(f"❌ Only {wom_with_fk}/{wom_total} WOM snapshots have user_id FKs")

if total_kills == 0:
    issues.append("❌ Total boss kills is 0 - WOM data may not be harvested")

if discord_with_fk < discord_total * 0.9:
    issues.append(f"❌ Only {discord_with_fk}/{discord_total} Discord messages have user_id FKs")

if not issues:
    print("✅ All data looks correct!")
else:
    for issue in issues:
        print(issue)

conn.close()
