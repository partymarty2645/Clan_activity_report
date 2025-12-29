import json
from collections import Counter

data_path = 'd:\\Clan_activity_report\\docs\\clan_data.json'

try:
    with open(data_path, 'r') as f:
        data = json.load(f)

    # Use 'allMembers'
    members = data.get('allMembers', [])
    dates = [m.get('joined_at') for m in members if m.get('joined_at')]
    date_counts = Counter(dates)
    
    # Creation Day
    creation = "2025-02-14"
    c_count = date_counts.get(creation, 0)
    
    # Remove creation to find next best
    if creation in date_counts:
        del date_counts[creation]

    # Top Waves
    top_dates = date_counts.most_common(3)
    
    print(f"Creation Day ({creation}): {c_count} Players")
    for date, count in top_dates:
        print(f"Wave: {date} -> {count} Players")
        
except Exception as e:
    print(f"Error: {e}")
