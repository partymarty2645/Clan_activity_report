import json
import os

JSON_PATH = "docs/clan_data.json"

def verify_gowi():
    if not os.path.exists(JSON_PATH):
        print(f"❌ JSON file not found: {JSON_PATH}")
        return

    with open(JSON_PATH, 'r') as f:
        data = json.load(f)

    # Search for Sir Gowi
    # keys are lowercased usernames?
    target = "sir gowi"
    
    # Check if data is list or dict
    # Current export format: list of objects? or dict?
    # Usually export_sqlite produces list.
    
    found = None
    
    # Handle the actual export format (Dict with 'allMembers' list)
    if isinstance(data, dict) and 'allMembers' in data:
        for p in data['allMembers']:
            if p.get('username', '').lower() == target:
                found = p
                break
    elif isinstance(data, list):
        for p in data:
            if p.get('username', '').lower() == target:
                found = p
                break
    if found:
        print(f"✅ Found '{target}' in JSON.")
        print(f"   - Messages (30d): {found.get('msgs_30d')}")
        print(f"   - Total Messages: {found.get('msgs_total')}")
        print(f"   - XP (30d): {found.get('xp_30d')}")
        print(f"   - Boss (30d): {found.get('boss_30d')}")
        
        if found.get('msgs_30d', 0) > 0:
             print("   ✅ Messages are populated.")
        else:
             print("   ⚠️  Messages are 0 (Check if this is correct).")
    else:
        print(f"❌ '{target}' NOT FOUND in JSON export!")

if __name__ == "__main__":
    verify_gowi()
