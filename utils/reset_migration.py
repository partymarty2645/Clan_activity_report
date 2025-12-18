
import sys
import os
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connector import SessionLocal, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)

def reset():
    with engine.connect() as conn:
        logging.info("Truncating/Deleting normalized tables...")
        conn.execute(text("DELETE FROM skill_snapshots"))
        conn.execute(text("DELETE FROM boss_snapshots"))
        conn.commit()
        logging.info("Done.")

if __name__ == "__main__":
    reset()
