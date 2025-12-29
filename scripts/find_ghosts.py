import json

data_path = 'clan_data.json'

try:
    with open(data_path, 'r') as f:
        data = json.load(f)

    members = data.get('allMembers', [])
    
    # Filter for Creation Day (2025-02-14)
    founders = [m for m in members if m.get('joined_at') == "2025-02-14"]
    
    print(f"Found {len(founders)} Founders.")
    
    # Sort by Messages (Ascending)
    founders.sort(key=lambda x: x.get('msgs_total', 0))
    
    print("Lowest Activity Founders:")
    for m in founders[:5]:
        print(f"{m['username']}: {m.get('msgs_total', 0)} Msgs, {m.get('total_xp', 0)} XP")

except Exception as e:
    print(f"Error: {e}")
