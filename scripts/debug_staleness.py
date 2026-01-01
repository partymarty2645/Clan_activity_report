from database.connector import SessionLocal
from database.models import WOMSnapshot
from sqlalchemy import select
from datetime import datetime, timezone
import sys

session = SessionLocal()
try:
    snap = session.execute(select(WOMSnapshot).order_by(WOMSnapshot.timestamp.desc()).limit(1)).scalar_one_or_none()
    if snap:
        print(f"Timestamp: {snap.timestamp}")
        print(f"Type: {type(snap.timestamp)}")
        print(f"Tzinfo: {snap.timestamp.tzinfo}")
        
        now_utc = datetime.now(timezone.utc)
        print(f"Now UTC: {now_utc}")
        print(f"Now Tzinfo: {now_utc.tzinfo}")
        
        try:
            diff = now_utc - snap.timestamp
            print(f"Diff: {diff}")
        except Exception as e:
            print(f"ERROR: {e}")

    # Check usernames
    print("\nSample Usernames in DB:")
    users = session.execute(select(WOMSnapshot.username).distinct().limit(10)).scalars().all()
    for u in users:
        print(f" - '{u}'")

    from core.usernames import UsernameNormalizer
    print(f"\nTest Normalization: 'Iron Man' -> '{UsernameNormalizer.normalize('Iron Man')}'")

except Exception as e:
    print(f"General Error: {e}")
finally:
    session.close()

