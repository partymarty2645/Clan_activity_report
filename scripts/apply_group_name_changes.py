import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from core.usernames import UsernameNormalizer
from database.connector import init_db, SessionLocal
from database.models import ClanMember
from services.wom import wom_client
from services.identity_service import ensure_member_alias, upsert_alias


async def apply_for_member(session, member: ClanMember) -> int:
    # Ensure their primary alias exists (current)
    ensure_member_alias(session, member, source="wom")

    # Fetch approved name changes via WOM client and upsert aliases
    changes = await wom_client.get_player_name_changes(member.username)
    updated = 0
    for entry in changes or []:
        status = entry.get("status")
        if status and status.lower() != "approved":
            continue
        old_name = entry.get("oldName") or entry.get("old_name")
        new_name = entry.get("newName") or entry.get("new_name")
        created_at_raw = entry.get("createdAt") or entry.get("created_at")
        seen_at = None
        if isinstance(created_at_raw, str):
            try:
                seen_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except Exception:
                seen_at = None
        for candidate, is_current in ((old_name, False), (new_name, True)):
            if candidate:
                try:
                    upsert_alias(session, member.id, candidate, source="wom", seen_at=seen_at, is_current=is_current)
                    updated += 1
                except Exception as e:
                    # Collision or invalid input; log and continue
                    print(f"[WARN] Alias upsert failed for {member.username} -> '{candidate}': {e}")
    return updated


async def main() -> int:
    print(f"Applying WOM-approved name changes for group {Config.WOM_GROUP_ID}...")
    # Initialize DB and open session
    init_db()
    session = SessionLocal()
    try:
        # Get members from WOM
        members = await wom_client.get_group_members(Config.WOM_GROUP_ID)
        # Build a lookup of member info by canonical/normalized username
        member_info: Dict[str, dict] = {}
        for m in members:
            uname = m.get('username') or m.get('displayName')
            if not uname:
                continue
            member_info[uname] = {
                'role': m.get('role'),
                'joined_at': m.get('joined_at') or m.get('createdAt')
            }
        usernames = list(member_info.keys())

        # Preload existing ClanMembers and build normalized lookup to avoid duplicates
        existing_members = session.query(ClanMember).all()
        norm_to_member: Dict[str, ClanMember] = {}
        for em in existing_members:
            try:
                norm = UsernameNormalizer.normalize(em.username, for_comparison=True)
                if norm and norm not in norm_to_member:
                    norm_to_member[norm] = em
            except Exception:
                continue

        applied_total = 0
        created_total = 0
        for uname in usernames:
            norm_uname = UsernameNormalizer.normalize(uname, for_comparison=True)
            cm: Optional[ClanMember] = None
            if norm_uname and norm_uname in norm_to_member:
                cm = norm_to_member[norm_uname]
            else:
                # Try exact match as a fallback
                cm = session.query(ClanMember).filter(ClanMember.username == uname).one_or_none()

            if not cm:
                # Create a provisional ClanMember row from WOM group data
                info = member_info.get(uname, {})
                cm = ClanMember(username=uname, role=info.get('role'))
                session.add(cm)
                try:
                    session.commit()
                    session.refresh(cm)
                    created_total += 1
                    # Update normalized cache
                    if norm_uname:
                        norm_to_member[norm_uname] = cm
                except Exception as e:
                    # UNIQUE constraint collision (row already exists). Skip creation.
                    session.rollback()
                    print(f"[SKIP] Could not create ClanMember for '{uname}': {e}")
                    # Attempt to fetch existing again in case of race/rollback
                    cm = session.query(ClanMember).filter(ClanMember.username == uname).one_or_none()
                    if not cm:
                        continue

            try:
                updated = await apply_for_member(session, cm)
                if updated:
                    print(f"[OK] {uname}: {updated} alias updates")
                    applied_total += updated
            except Exception as e:
                print(f"[WARN] Failed to apply for '{uname}': {e}")

        print(f"Done. Members seen: {len(usernames)} | Aliases upserted: {applied_total} | Newly added ClanMember rows: {created_total}")
        return 0
    finally:
        await wom_client.close()
        session.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
