import asyncio
import sys
from pathlib import Path
from typing import Dict, List

# Ensure project root on path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from services.wom import wom_client


async def fetch_group_members() -> List[Dict]:
    return await wom_client.get_group_members(Config.WOM_GROUP_ID)


async def fetch_member_name_changes(username: str, limit: int = 50):
    try:
        # Prefer the per-player endpoint (approved changes only)
        result = await wom_client.get_player_name_changes(username)
        return result or []
    except Exception as e:
        print(f"[WARN] name-changes fetch failed for {username}: {e}")
        return []


async def main():
    print(f"Fetching group members from WOM group {Config.WOM_GROUP_ID}...")
    members = await fetch_group_members()
    usernames = [m.get('username') or m.get('displayName') for m in members if (m.get('username') or m.get('displayName'))]
    print(f"Found {len(usernames)} members. Fetching name changes...")

    # Fetch in batches with WOMClient's internal rate limiting
    tasks = [fetch_member_name_changes(u, limit=100) for u in usernames]
    results = await asyncio.gather(*tasks)

    total_changes = 0
    for u, changes in zip(usernames, results):
        if changes:
            print(f"=== {u} ===")
            for idx, entry in enumerate(changes, start=1):
                old_name = entry.get('oldName') or entry.get('old_name')
                new_name = entry.get('newName') or entry.get('new_name')
                created_at = entry.get('createdAt') or entry.get('created_at')
                status = entry.get('status')
                print(f"{idx}. {old_name} -> {new_name} at {created_at} status={status}")
            print()
            total_changes += len(changes)

    print(f"Done. Members: {len(usernames)} | Total name-change entries: {total_changes}")
    await wom_client.close()


if __name__ == '__main__':
    asyncio.run(main())
