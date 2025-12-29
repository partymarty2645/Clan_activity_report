import sqlite3

conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("TABLES:")
print("=" * 60)
for table in tables:
    table_name = table[0]
    print(f"\n{table_name}:")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        col_id, col_name, col_type, notnull, default, pk = col
        print(f"  {col_name}: {col_type} {'PK' if pk else ''}")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  Rows: {count}")

conn.close()
