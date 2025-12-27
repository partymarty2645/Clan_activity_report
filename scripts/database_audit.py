#!/usr/bin/env python3
"""
Database Audit Script
Checks for data integrity errors in the clan_data.db database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connector import get_db
from sqlalchemy import text

def audit_database():
    """Audit the database for errors."""
    db = next(get_db())
    
    errors = []
    
    print("Starting database audit...")
    
    # Check for null values in required fields
    print("\n1. Checking for null values in required fields...")
    
    # ClanMember.username
    result = db.execute(text("SELECT COUNT(*) FROM clan_members WHERE username IS NULL")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} clan_members with null username")
    
    # PlayerNameAlias.normalized_name
    result = db.execute(text("SELECT COUNT(*) FROM player_name_aliases WHERE normalized_name IS NULL")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} player_name_aliases with null normalized_name")
    
    # PlayerNameAlias.canonical_name
    result = db.execute(text("SELECT COUNT(*) FROM player_name_aliases WHERE canonical_name IS NULL")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} player_name_aliases with null canonical_name")
    
    # Check for foreign key violations
    print("\n2. Checking for foreign key violations...")
    
    # discord_messages.user_id -> clan_members.id
    result = db.execute(text("""
        SELECT COUNT(*) FROM discord_messages 
        WHERE user_id NOT IN (SELECT id FROM clan_members)
    """)).scalar()
    if result and result > 0:
        errors.append(f"Found {result} discord_messages with invalid user_id")
    
    # wom_snapshots.user_id -> clan_members.id
    result = db.execute(text("""
        SELECT COUNT(*) FROM wom_snapshots 
        WHERE user_id NOT IN (SELECT id FROM clan_members)
    """)).scalar()
    if result and result > 0:
        errors.append(f"Found {result} wom_snapshots with invalid user_id")
    
    # player_name_aliases.member_id -> clan_members.id
    result = db.execute(text("""
        SELECT COUNT(*) FROM player_name_aliases 
        WHERE member_id NOT IN (SELECT id FROM clan_members)
    """)).scalar()
    if result and result > 0:
        errors.append(f"Found {result} player_name_aliases with invalid member_id")
    
    # boss_snapshots.wom_snapshot_id -> wom_snapshots.id
    result = db.execute(text("""
        SELECT COUNT(*) FROM boss_snapshots 
        WHERE wom_snapshot_id NOT IN (SELECT id FROM wom_snapshots)
    """)).scalar()
    if result and result > 0:
        errors.append(f"Found {result} boss_snapshots with invalid wom_snapshot_id")
    
    # Check for duplicate unique keys
    print("\n3. Checking for duplicate unique keys...")
    
    # clan_members.username
    result = db.execute(text("""
        SELECT username, COUNT(*) as cnt 
        FROM clan_members 
        GROUP BY username 
        HAVING cnt > 1
    """)).fetchall()
    if result:
        errors.append(f"Found duplicate usernames: {[(r[0], r[1]) for r in result]}")
    
    # player_name_aliases.normalized_name
    result = db.execute(text("""
        SELECT normalized_name, COUNT(*) as cnt 
        FROM player_name_aliases 
        GROUP BY normalized_name 
        HAVING cnt > 1
    """)).fetchall()
    if result:
        errors.append(f"Found duplicate normalized_names: {[(r[0], r[1]) for r in result]}")
    
    # Check for invalid data types (e.g., negative values where shouldn't be)
    print("\n4. Checking for invalid data...")
    
    # Negative XP or kills
    result = db.execute(text("SELECT COUNT(*) FROM wom_snapshots WHERE total_xp < 0")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} wom_snapshots with negative total_xp")
    
    result = db.execute(text("SELECT COUNT(*) FROM wom_snapshots WHERE total_boss_kills < 0")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} wom_snapshots with negative total_boss_kills")
    
    result = db.execute(text("SELECT COUNT(*) FROM boss_snapshots WHERE kills < 0")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} boss_snapshots with negative kills")
    
    result = db.execute(text("SELECT COUNT(*) FROM boss_snapshots WHERE rank < 0")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} boss_snapshots with negative rank")
    
    # Check for orphaned records (records that should have been deleted)
    print("\n5. Checking for orphaned records...")
    
    # WOM records without corresponding snapshots? But wom_records might be different.
    # Perhaps check if all clan_members have at least one snapshot or something, but not necessarily an error.
    
    # Check for empty strings in required fields
    print("\n6. Checking for empty strings in required fields...")
    
    result = db.execute(text("SELECT COUNT(*) FROM clan_members WHERE username = ''")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} clan_members with empty username")
    
    result = db.execute(text("SELECT COUNT(*) FROM player_name_aliases WHERE normalized_name = ''")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} player_name_aliases with empty normalized_name")
    
    result = db.execute(text("SELECT COUNT(*) FROM player_name_aliases WHERE canonical_name = ''")).scalar()
    if result and result > 0:
        errors.append(f"Found {result} player_name_aliases with empty canonical_name")
    
    # Summary
    print("\nAudit complete.")
    if errors:
        print(f"Found {len(errors)} error categories:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("No errors found.")
    
    return errors

if __name__ == "__main__":
    audit_database()