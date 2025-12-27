import sys
import os
sys.path.append(os.getcwd())
from database.connector import SessionLocal
from core.analytics import AnalyticsService
from services.identity_service import _fetch_wom_name_changes_by_username

def check_name_changes():
    session = SessionLocal()
    analytics = AnalyticsService(session)
    latest = analytics.get_latest_snapshots()
    
    # 1. Identify Target Users
    targets = []
    for user, snap in latest.items():
        if snap.total_boss_kills == 0:
            targets.append(user)
            
    print(f"Checking {len(targets)} users for name changes...\n")
    
    found_changes = 0
    
    for t in targets:
        print(f"Checking {t}...")
        try:
            changes = _fetch_wom_name_changes_by_username(t)
            if changes:
                found_changes += 1
                latest_change = changes[0] # assuming sorted? usually API returns list.
                # Inspect structure
                new_name = latest_change.get("newName") or latest_change.get("new_name")
                status = latest_change.get("status")
                print(f"✅ FOUND CHANGE: {t} -> {new_name} (Status: {status})")
            else:
                print(f"❌ No changes found for {t}")
        except Exception as e:
            print(f"⚠️ Error checking {t}: {e}")
            
    print(f"\nSummary: Found name changes for {found_changes} / {len(targets)} users.")

if __name__ == "__main__":
    check_name_changes()
