from sqlalchemy import create_engine, text
from database.connector import DB_URL

def add_indices():
    print(f"Connecting to {DB_URL}...")
    engine = create_engine(DB_URL)
    
    indices = [
        ("idx_boss_snapshots_boss_name", "boss_snapshots", "boss_name"),
        ("idx_skill_snapshots_skill_name", "skill_snapshots", "skill_name")
    ]
    
    with engine.connect() as conn:
        for idx_name, table, col in indices:
            print(f"Adding index {idx_name} on {table}({col})...")
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})"))
                print("Success.")
            except Exception as e:
                print(f"Failed: {e}")

if __name__ == "__main__":
    add_indices()
