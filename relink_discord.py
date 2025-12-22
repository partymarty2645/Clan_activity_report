#!/usr/bin/env python3
"""Re-link discord_messages to clan_members using corrected IDs."""

import sqlite3

conn = sqlite3.connect('clan_data.db')
c = conn.cursor()

print("RE-LINKING discord_messages to members...")
print("=" * 80)

# Check current state
c.execute('SELECT COUNT(*) FROM discord_messages WHERE user_id IS NOT NULL')
linked_before = c.fetchone()[0]

print(f"\nBefore:")
print(f"  Linked messages: {linked_before}/587222 ({100*linked_before/587222:.1f}%)")

# Re-link using case-insensitive match
c.execute("""
    UPDATE discord_messages
    SET user_id = (
        SELECT id FROM clan_members 
        WHERE LOWER(clan_members.username) = LOWER(discord_messages.author_name)
    )
    WHERE author_name IS NOT NULL
""")

conn.commit()

# Check result
c.execute('SELECT COUNT(*) FROM discord_messages WHERE user_id IS NOT NULL')
linked_after = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM discord_messages WHERE user_id IS NULL')
unlinked = c.fetchone()[0]

print(f"\nAfter:")
print(f"  Linked messages: {linked_after}/587222 ({100*linked_after/587222:.1f}%)")
print(f"  Unlinked messages: {unlinked}/587222 ({100*unlinked/587222:.1f}%)")
print(f"  Improvement: +{linked_after - linked_before} new links")

# Sample matched messages
print(f"\nSample of newly linked messages:")
c.execute("""
    SELECT author_name, user_id, COUNT(*) as msg_count
    FROM discord_messages 
    WHERE user_id IS NOT NULL
    GROUP BY user_id
    ORDER BY msg_count DESC
    LIMIT 10
""")

for author, user_id, count in c.fetchall():
    print(f"  {author:<30} (ID {user_id:>4}): {count:>6} messages")

print(f"\n✅ Discord messages linked to clan_members using corrected IDs!")

conn.close()
