import json
import sys

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed in the venv.")
    print("Try: D:/Clan_activity_report/.venv/Scripts/pip.exe install requests")
    sys.exit(2)

try:
    from core.config import Config
except Exception as e:
    print("ERROR: Could not import core.config:", e)
    sys.exit(3)

base = Config.WOM_BASE_URL or "https://api.wiseoldman.net/v2"
group_id = str(Config.WOM_GROUP_ID or "11114").strip()
url = f"{base}/groups/{group_id}"

print(f"Pinging WOM API: GET {url}")
try:
    resp = requests.get(url, timeout=20)
    print(f"Status: {resp.status_code}")
    ct = resp.headers.get('Content-Type', '')
    print(f"Content-Type: {ct}")
    if resp.ok:
        data = resp.json()
        # Print minimal summary
        name = data.get('name') or data.get('displayName') or 'Unknown'
        members_count = data.get('membersCount') or data.get('memberCount') or 'n/a'
        created_at = data.get('createdAt') or data.get('created_at') or 'n/a'
        print("Response summary:")
        print(f"  Group: {name} (ID: {group_id})")
        print(f"  Members count: {members_count}")
        print(f"  Created at: {created_at}")
        # Show first 5 keys for sanity
        print("  Keys:", ", ".join(list(data.keys())[:5]))
        sys.exit(0)
    else:
        print("Response body (first 300 chars):")
        print(resp.text[:300])
        sys.exit(1)
except requests.RequestException as e:
    print("Network/Request error:", e)
    sys.exit(4)
