import json

with open('e:/Clan_activity_report/clan_data.json', 'r') as f:
    data = json.load(f)
    print(f"Total members: {len(data['allMembers'])}")
    if len(data['allMembers']) > 0:
        # Get a sample member
        sample = data['allMembers'][0]
        print("Sample Member Keys:", sample.keys())
        print("Sample Member Data:", json.dumps(sample, indent=2))
        
        # Check unique roles
        roles = set(m.get('role', 'Unknown') for m in data['allMembers'])
        print("\nUnique Roles Found:", roles)
        
        # Check boss keys in a member (if they exist)
        if 'bosses' in sample:
            print("Boss keys:", list(sample['bosses'].keys())[:5])
        elif 'bossKills' in sample: # Sometimes it's flat or in a sub-dict
             print("Boss Kills:", sample['bossKills'])
        
        # Check if there is a 'bosses' dict in member or if we have to cross-reference
        # Look for raid specific keys
        raids = ['Chambers of Xeric', 'Theatre of Blood', 'Tombs of Amascut']
        print("\nChecking for raids in first 5 members:")
        for m in data['allMembers'][:5]:
            print(f"{m['name']}:")
            # Assuming 'bosses' dict exists map
            if 'bosses' in m:
                for r in raids:
                    print(f"  {r}: {m['bosses'].get(r, 'N/A')}")
