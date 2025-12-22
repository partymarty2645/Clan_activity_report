#!/usr/bin/env python3
"""Verify IDs were actually fixed."""

import sqlite3

conn = sqlite3.connect('clan_data.db')
c = conn.cursor()

print("FINAL VERIFICATION")
print("=" * 80)

# Check clan_members IDs
c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NULL')
null_ids = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NOT NULL')
with_ids = c.fetchone()[0]

print(f"\nclan_members: {with_ids} with IDs, {null_ids} without IDs")

# Check discord_messages user_id FKs  
c.execute('SELECT COUNT(*) FROM discord_messages WHERE user_id IS NOT NULL')
linked = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM discord_messages')
total = c.fetchone()[0]

print(f"discord_messages: {linked}/{total} linked ({100*linked/total:.1f}%)")

# Check wom_snapshots user_id FKs
c.execute('SELECT COUNT(*) FROM wom_snapshots WHERE user_id IS NOT NULL')
wom_linked = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM wom_snapshots')
wom_total = c.fetchone()[0]

print(f"wom_snapshots: {wom_linked}/{wom_total} linked ({100*wom_linked/wom_total:.1f}%)")

print("\n" + "=" * 80)
if null_ids == 0 and with_ids == 404:
    print("✅ FIXED: All clan_members now have IDs!")
else:
    print(f"❌ ISSUE: {null_ids} members still without IDs")

conn.close()
