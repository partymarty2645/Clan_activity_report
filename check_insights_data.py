import sqlite3

conn = sqlite3.connect('clan_data.db')
conn.row_factory = sqlite3.Row

print("=== CHECKING DATA IN WOM_RECORDS ===\n")

# Check counts
cursor = conn.execute("SELECT COUNT(*) as cnt FROM wom_records;")
print(f"Total wom_records rows: {cursor.fetchone()['cnt']}\n")

# Check msg_custom distribution
cursor = conn.execute("""
    SELECT 
        COUNT(*) as cnt,
        COUNT(CASE WHEN msg_custom > 0 THEN 1 END) as has_msgs,
        COUNT(CASE WHEN msg_custom IS NULL THEN 1 END) as null_msgs,
        AVG(CAST(msg_custom AS FLOAT)) as avg_msgs,
        MAX(msg_custom) as max_msgs
    FROM wom_records;
""")
row = cursor.fetchone()
print(f"msg_custom stats:")
print(f"  Total records: {row['cnt']}")
print(f"  Records with msgs > 0: {row['has_msgs']}")
print(f"  NULL msgs: {row['null_msgs']}")
print(f"  Average: {row['avg_msgs']}")
print(f"  Max: {row['max_msgs']}\n")

# Check xp_custom distribution
cursor = conn.execute("""
    SELECT 
        COUNT(CASE WHEN xp_custom > 0 THEN 1 END) as has_xp,
        COUNT(CASE WHEN xp_custom IS NULL THEN 1 END) as null_xp,
        AVG(CAST(xp_custom AS FLOAT)) as avg_xp,
        MAX(xp_custom) as max_xp
    FROM wom_records;
""")
row = cursor.fetchone()
print(f"xp_custom stats:")
print(f"  Records with xp > 0: {row['has_xp']}")
print(f"  NULL xp: {row['null_xp']}")
print(f"  Average: {row['avg_xp']}")
print(f"  Max: {row['max_xp']}\n")

# Check if there are any members with BOTH msg > 10 AND xp > 100000
cursor = conn.execute("""
    SELECT COUNT(*) as cnt FROM wom_records 
    WHERE msg_custom > 10 AND xp_custom > 100000;
""")
print(f"Members with msg_custom > 10 AND xp_custom > 100000: {cursor.fetchone()['cnt']}\n")

# Check if there are any members with msg > 0
cursor = conn.execute("""
    SELECT COUNT(*) as cnt FROM wom_records 
    WHERE msg_custom > 0;
""")
print(f"Members with msg_custom > 0: {cursor.fetchone()['cnt']}\n")

# Sample rows
print("=== SAMPLE DATA ===")
cursor = conn.execute("SELECT username, xp_custom, msg_custom FROM wom_records LIMIT 5;")
for row in cursor.fetchall():
    print(f"  {row['username']}: xp={row['xp_custom']}, msg={row['msg_custom']}")
