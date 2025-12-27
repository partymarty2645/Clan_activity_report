import sys
import os
sys.path.append(os.getcwd())
from database.connector import SessionLocal
from database.models import ClanMember
from core.analytics import AnalyticsService

def count_stats():
    session = SessionLocal()
    analytics = AnalyticsService(session)
    
    # 1. Total Members in DB
    total_members = session.query(ClanMember).count()
    
    # 2. Members with Snapshots (Linked)
    latest = analytics.get_latest_snapshots()
    linked_count = len(latest)
    
    # 3. Members with > 0 XP (Data Verified)
    valid_xp_count = 0
    for snap in latest.values():
        if snap.total_xp > 0:
            valid_xp_count += 1
            
    # 4. Zero Boss Kills (just for context)
    zero_boss_count = 0
    for snap in latest.values():
        if snap.total_boss_kills == 0:
            zero_boss_count += 1
            
    print(f"--- Final Stats ---")
    print(f"Total Members in DB: {total_members}")
    print(f"Linked (Have Snapshot): {linked_count}")
    print(f"Valid Data (>0 XP): {valid_xp_count}")
    print(f"Zero Boss Kills (Verified): {zero_boss_count}")
    
    from core.usernames import UsernameNormalizer

    # Normalize sets for comparison to avoid case-sensitivity issues
    today_active = {UsernameNormalizer.normalize(m.username, for_comparison=True) for m in session.query(ClanMember).all()}
    
    # keys in get_latest_snapshots are already normalized by AnalyticsService now?
    # Let's double check key format. AnalyticsService.get_latest_snapshots returns normalized keys if updated, 
    # but based on previous context, it returns {username: snap}. 
    # Let's ensure we normalize these keys too just in case.
    snap_users = {UsernameNormalizer.normalize(u, for_comparison=True) for u in latest.keys()}
    
    # 1. Members missing Data (Problem!)
    missing_data = today_active - snap_users
    
    # 2. Orphans (Data exists, but user deleted from DB)
    orphans = snap_users - today_active
    
    print(f"\n--- Detailed Analysis ---")
    print(f"Active Roster Size (Normalized): {len(today_active)}")
    print(f"Snapshot Users (Normalized): {len(snap_users)}")
    
    print(f"\n[Problem] Active Members with NO Data: {len(missing_data)}")
    if missing_data:
        print(f" -> {sorted(list(missing_data))}")
        
    print(f"\n[Info] Orphan Snapshots (Ghosts): {len(orphans)}")
    if orphans:
        print(f" -> {sorted(list(orphans))}")
        
    print(f"\n✅ CORRECTLY LINKED (In Plan): {len(today_active & snap_users)}")

if __name__ == "__main__":
    count_stats()
