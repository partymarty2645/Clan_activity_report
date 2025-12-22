
import json
import os

def check():
    path = "clan_data.json"
    if not os.path.exists(path):
        print("clan_data.json not found!")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    target = "theforgegod"
    found = False
    
    for m in data.get('allMembers', []):
        if m['username'].lower() == target.lower():
            print(f"✅ Found {m['username']}")
            print(f"   - Msgs Total: {m.get('msgs_total')}")
            print(f"   - Msgs 7d:    {m.get('msgs_7d')}")
            found = True
            break
            
    if not found:
        print(f"❌ User '{target}' not found in JSON.")

if __name__ == "__main__":
    check()
