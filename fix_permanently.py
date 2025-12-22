#!/usr/bin/env python3
"""
Permanently fix clan_members IDs.
This script:
1. Sets all NULL IDs to their ROWID
2. Re-links discord_messages to the corrected IDs
3. Commits the changes
"""

import sqlite3

print("PERMANENT FIX: Populate clan_members IDs")
print("=" * 80)

conn = sqlite3.connect('clan_data.db')
conn.isolation_level = None  # Auto-commit mode
c = conn.cursor()

# Step 1: Check before
c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NULL')
before_null = c.fetchone()[0]
print(f"\nBefore: {before_null} members without IDs")

# Step 2: Assign IDs based on ROWID
print("\nAssigning IDs based on ROWID...")
c.execute("UPDATE clan_members SET id = rowid WHERE id IS NULL")

# Step 3: Verify
c.execute('SELECT COUNT(*) FROM clan_members WHERE id IS NULL')
after_null = c.fetchone()[0]
print(f"After: {after_null} members without IDs")

if after_null == 0:
    print("✅ All members now have IDs!")
else:
    print(f"⚠️  Still {after_null} members without IDs")

# Step 4: Re-link discord messages
print("\nRe-linking discord_messages...")
c.execute("""
    UPDATE discord_messages
    SET user_id = (
        SELECT id FROM clan_members 
        WHERE LOWER(clan_members.username) = LOWER(discord_messages.author_name)
    )
    WHERE author_name IS NOT NULL
    AND user_id IS NULL
""")

# Check result
c.execute('SELECT COUNT(*) FROM discord_messages WHERE user_id IS NOT NULL')
total_linked = c.fetchone()[0]
print(f"✅ Total messages linked: {total_linked}/587233")

# Close properly
conn.close()

print("\n✅ Database permanently fixed!")
