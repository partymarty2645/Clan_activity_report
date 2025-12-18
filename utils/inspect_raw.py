
import sys
import os
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connector import SessionLocal
from database.models import WOMSnapshot
from sqlalchemy import select

def inspect_bad_data():
    db = SessionLocal()
    try:
        # Fetch one of the IDs that failed in the log
        bad_id = 45675
        snap = db.get(WOMSnapshot, bad_id)
        if snap:
            print(f"ID: {bad_id}")
            print(f"Raw Data Type: {type(snap.raw_data)}")
            print(f"Raw Data Repr: {repr(snap.raw_data)}")
            print(f"Raw Data Length: {len(snap.raw_data) if snap.raw_data else 0}")
        else:
            print(f"ID {bad_id} not found.")

        # Check a valid one if any
        stmt = select(WOMSnapshot).where(WOMSnapshot.raw_data != None).limit(1)
        good = db.execute(stmt).scalars().first()
        if good:
             print(f"Good ID: {good.id}")
             print(f"Good Data Start: {good.raw_data[:50]}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_bad_data()
