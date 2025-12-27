import sys
import os
sys.path.append(os.getcwd())
from core.analytics import AnalyticsService
from database.connector import SessionLocal
from core.usernames import UsernameNormalizer

def check_final_two():
    session = SessionLocal()
    analytics = AnalyticsService(session)
    latest = analytics.get_latest_snapshots()
    
    users = ['cervixthumpr', 'sulkypeen']
    found = 0
    
    for u in users:
        norm = UsernameNormalizer.normalize(u)
        if norm in latest:
            print(f"✅ {u} HAS DATA (XP: {latest[norm].total_xp})")
            found += 1
        else:
            print(f"❌ {u} STILL MISSING DATA")
            
    print(f"Found {found}/{len(users)}")
    return found == len(users)

if __name__ == "__main__":
    check_final_two()
