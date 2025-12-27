import sys
import os
from collections import defaultdict
sys.path.append(os.getcwd())
from database.connector import SessionLocal
from database.models import ClanMember, WOMSnapshot
from core.usernames import UsernameNormalizer

def deduplicate():
    session = SessionLocal()
    try:
        members = session.query(ClanMember).all()
        print(f"Starting Count: {len(members)}")
        
        # Group by "Aggressive Normalization" (to find the pairs)
        agg_map = defaultdict(list)
        for m in members:
            # aggressive norm = remove all non-alnum
            agg = ''.join(c for c in m.username if c.isalnum()).lower()
            agg_map[agg].append(m)
            
        merged_count = 0
        
        for agg, group in agg_map.items():
            if len(group) < 2:
                continue
                
            # We found a duplicate group!
            # Determine which one is the "Keeper"
            # The Keeper should be the one that matches our CURRENT normalization Logic
            # But wait, our Aggressive Norm finds them because they share chars.
            # We want to keep `noob man` (with spaces) over `noobman` (nospaces) IF WOM uses spaces.
            
            # Simple Heuristic:
            # 1. Prefer the one that matches UsernameNormalizer.normalize(name) self-consistency?
            #    No, because normalize('noobman') -> 'noobman'.
            # 2. Prefer the one with spaces/underscores?
            # 3. Prefer the one with the HIGHEST ID (newest)?
            
            # actually, harvest just ran. The "New" correct ones are likely the most recently added.
            # Let's check IDs.
            sorted_group = sorted(group, key=lambda x: x.id, reverse=True)
            keeper = sorted_group[0] # Newest ID is likely the one from recent harvest
            stales = sorted_group[1:]
            
            print(f"Group '{agg}':")
            print(f"  Keeping: '{keeper.username}' (ID: {keeper.id})")
            
            for stale in stales:
                print(f"  Merging: '{stale.username}' (ID: {stale.id})")
                
                # 1. Re-link Snapshots
                snaps = session.query(WOMSnapshot).filter(WOMSnapshot.user_id == stale.id).all()
                if snaps:
                    print(f"    -> Moving {len(snaps)} snapshots to Keeper.")
                    for s in snaps:
                        s.user_id = keeper.id
                        # Note: This might cause Unique Constraint violations if Keeper already 
                        # has a snapshot for the same timestamp.
                        # Let's trust Sqlite/SQLAlchemy to complain or we handle it?
                        # Actually, better to catch it.
                
                # 2. Delete Stale Member
                session.delete(stale)
                merged_count += 1
        
        try:
            session.commit()
            print(f"\n✅ Merge Complete. Removed {merged_count} duplicates.")
        except Exception as e:
            session.rollback()
            print(f"❌ Transaction Failed: {e}")
            print("Rolling back...")
            
    finally:
        session.close()

if __name__ == "__main__":
    deduplicate()
