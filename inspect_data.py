import json

try:
    with open('d:/Clan_activity_report/clan_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print("KEYS:", data.keys())
    
    if 'history' in data:
        print("Found 'history' key")
        hist = data['history']
        print(f"Type: {type(hist)}")
        if isinstance(hist, list) and len(hist) > 0:
            print(f"First Item: {hist[0]}")
        elif isinstance(hist, dict):
             print(f"Keys: {hist.keys()}")
    elif 'clan_history' in data:
        print("Found 'clan_history' key")
        print("Clan History keys:", data['clan_history'].keys())
    else:
        print("Neither 'history' nor 'clan_history' found")

    if 'activity_heatmap' in data:
        print("Found 'activity_heatmap', len:", len(data['activity_heatmap']))
    
    if 'topXPYear' in data:
        print("Found 'topXPYear', len:", len(data['topXPYear']))

except Exception as e:
    print(f"Error: {e}")
