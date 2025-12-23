import logging
from datetime import datetime, UTC
from typing import Optional, List, Dict

import requests
from sqlalchemy.orm import Session

from core.config import Config
from core.usernames import UsernameNormalizer
from database.models import PlayerNameAlias, ClanMember

logger = logging.getLogger("IdentityService")


def _now() -> datetime:
    # Use timezone-aware UTC timestamps to avoid comparison issues
    return datetime.now(UTC)


def upsert_alias(
    db: Session,
    member_id: int,
    name: str,
    source: str = "unknown",
    seen_at: Optional[datetime] = None,
    is_current: bool = False,
) -> PlayerNameAlias:
    """
    Create or update a `PlayerNameAlias` entry for a given `member_id`.

    Uses `UsernameNormalizer` to compute normalized and canonical forms.
    Enforces unique `normalized_name` to prevent silent collisions.
    """
    if not name:
        raise ValueError("name is required")

    norm = UsernameNormalizer.normalize(name, for_comparison=True)
    canon = UsernameNormalizer.canonical(name)
    if not norm:
        raise ValueError("normalized name is empty (invalid input)")

    alias = db.query(PlayerNameAlias).filter(PlayerNameAlias.normalized_name == norm).one_or_none()

    if alias:
        # Update existing alias metadata
        alias.member_id = member_id
        alias.canonical_name = canon
        alias.source = source or alias.source
        ts = (seen_at or _now()).replace(tzinfo=None)
        alias.last_seen_at = max(alias.last_seen_at or ts, ts)
        alias.first_seen_at = min(alias.first_seen_at or ts, ts)
        alias.is_current = bool(is_current)
        db.add(alias)
        db.commit()
        db.refresh(alias)
        return alias

    # Create new alias
    ts = (seen_at or _now()).replace(tzinfo=None)
    alias = PlayerNameAlias(
        member_id=member_id,
        normalized_name=norm,
        canonical_name=canon,
        source=source,
        first_seen_at=ts,
        last_seen_at=ts,
        is_current=bool(is_current),
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


def resolve_member_by_name(db: Session, name: str) -> Optional[int]:
    """
    Resolve a `ClanMember.id` from any known alias name.

    Returns `member_id` if found, else None.
    """
    if not name:
        return None

    norm = UsernameNormalizer.normalize(name, for_comparison=True)
    if not norm:
        return None

    alias = db.query(PlayerNameAlias).filter(PlayerNameAlias.normalized_name == norm).one_or_none()
    return alias.member_id if alias else None


def _wom_headers() -> Dict[str, str]:
    return {
        "x-api-key": Config.WOM_API_KEY or "",
        "accept": "application/json",
    }


def _fetch_wom_name_changes_by_username(username: str) -> Optional[List[Dict]]:
    """
    Try fetching name changes from WOM by username.

    The WOM API offers name change data; exact route may differ by version.
    We attempt common patterns and return the first successful payload.
    """
    base = Config.WOM_BASE_URL.rstrip("/")
    candidates = [
        f"{base}/players/username/{username}/name-changes",
        f"{base}/name-changes?username={username}",
        f"{base}/players/{username}/name-changes",
    ]

    for url in candidates:
        try:
            resp = requests.get(url, headers=_wom_headers(), timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                # Normalise expected payload to list of entries
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]
                if isinstance(data, list):
                    return data
            elif resp.status_code == 404:
                continue
        except Exception as e:
            logger.debug(f"WOM name changes fetch failed for {url}: {e}")
            continue
    return None


def sync_wom_name_changes(db: Session, member_id: int, primary_name: str) -> int:
    """
    Pull name change history from WOM for a given player and upsert aliases.

    Returns the number of aliases inserted/updated.
    """
    if not primary_name:
        return 0

    changes = _fetch_wom_name_changes_by_username(primary_name)
    if not changes:
        return 0

    updated = 0
    for entry in changes:
        # Expected shape may include fields such as: 'oldName', 'newName', 'createdAt', 'resolvedAt', 'status'
        # We'll capture both ends of a change as aliases
        old_name = entry.get("oldName") or entry.get("old_name")
        new_name = entry.get("newName") or entry.get("new_name")
        created_at_raw = entry.get("createdAt") or entry.get("created_at")

        seen_at = None
        if isinstance(created_at_raw, str):
            try:
                # WOM uses ISO 8601 timestamps
                seen_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except Exception:
                seen_at = None

        for candidate, is_current in ((old_name, False), (new_name, True)):
            if candidate:
                try:
                    upsert_alias(db, member_id, candidate, source="wom", seen_at=seen_at, is_current=is_current)
                    updated += 1
                except Exception as e:
                    # Collision or invalid input; log and continue
                    logger.warning(f"Alias upsert failed for member {member_id}, name '{candidate}': {e}")
                    continue

    return updated


def ensure_member_alias(db: Session, member: ClanMember, source: str = "game") -> PlayerNameAlias:
    """
    Ensure the member's primary username is present in aliases.
    """
    return upsert_alias(db, member_id=member.id, name=member.username, source=source, seen_at=_now(), is_current=True)
