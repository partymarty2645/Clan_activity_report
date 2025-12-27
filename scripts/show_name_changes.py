import argparse
import sys
from typing import List, Optional
from pathlib import Path

from sqlalchemy.orm import Session

# Ensure project root is on sys.path for module imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from core.usernames import UsernameNormalizer
from database.connector import init_db, SessionLocal
from database.models import ClanMember, PlayerNameAlias
from services.identity_service import (
    _fetch_wom_name_changes_by_username,
    resolve_member_by_name,
    sync_wom_name_changes,
)


def print_changes(username: str, changes: Optional[List[dict]]) -> None:
    print(f"=== WOM name changes for: {username} ===")
    if changes is None:
        print("API Error or Endpoint Unavailable.")
        return
    if not changes:
        print("No name changes found.")
        return

    for idx, entry in enumerate(changes, start=1):
        old_name = entry.get("oldName") or entry.get("old_name")
        new_name = entry.get("newName") or entry.get("new_name")
        created_at = entry.get("createdAt") or entry.get("created_at")
        status = entry.get("status")
        print(f"{idx}. {old_name} -> {new_name} at {created_at} status={status}")
    print()


def print_aliases(db: Session, member_id: int) -> None:
    aliases = (
        db.query(PlayerNameAlias)
        .filter(PlayerNameAlias.member_id == member_id)
        .order_by(PlayerNameAlias.last_seen_at.desc().nulls_last())
        .all()
    )
    print(f"--- Aliases for member_id={member_id} ---")
    if not aliases:
        print("No aliases stored.")
        return
    for a in aliases:
        print(
            f"canonical='{a.canonical_name}' | normalized='{a.normalized_name}' | "
            f"source={a.source} | current={a.is_current} | first_seen={a.first_seen_at} | last_seen={a.last_seen_at}"
        )
    print()


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Show WOM name changes and optional alias application")
    parser.add_argument("--username", "-u", action="append", help="OSRS username to check (can repeat)")
    parser.add_argument("--limit", "-n", type=int, default=1000, help="When no username provided, show first N clan members")
    parser.add_argument("--apply", action="store_true", help="Apply changes to aliases if member can be resolved")
    args = parser.parse_args(argv)

    # Initialize DB
    init_db()
    db = SessionLocal()

    try:
        usernames = args.username or []

        if not usernames:
            members = db.query(ClanMember).order_by(ClanMember.id.asc()).limit(args.limit).all()
            usernames = [m.username for m in members]
            if not usernames:
                print("No clan members found. Provide --username to query directly.")
                return 0

        import time # Added for rate limiting

        for i, uname in enumerate(usernames):
            if i > 0:
                time.sleep(0.7) # Respect WOM rate limit (~90 RPM)

            changes = _fetch_wom_name_changes_by_username(uname)
            print_changes(uname, changes)

            if args.apply:
                # Try exact member match first, then alias resolution
                member = db.query(ClanMember).filter(ClanMember.username == uname).one_or_none()
                member_id = member.id if member else resolve_member_by_name(db, uname)

                if member_id:
                    updated = sync_wom_name_changes(db, member_id, uname)
                    print(f"Applied {updated} alias updates.")
                    print_aliases(db, member_id)
                else:
                    # Create a provisional member? Prefer manual resolution.
                    norm = UsernameNormalizer.normalize(uname)
                    print(f"Could not resolve member for '{uname}' (normalized='{norm}'). Skipped apply.")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
