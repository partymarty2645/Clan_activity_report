import sqlite3
conn = sqlite3.connect('clan_data.db')
cursor = conn.cursor()
cursor.execute("SELECT version_num FROM alembic_version")
version = cursor.fetchone()
print(f"Current Alembic version: {version[0] if version else 'None'}")
conn.close()
