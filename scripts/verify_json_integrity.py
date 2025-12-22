import json
import os

try:
    with open('clan_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total Members: {len(data.get('allMembers', []))}")
    print("\n--- TOP BOSSERS (Grid Candidates) ---")
    bossers = data.get('topBossers', [])
    
    found_custom = 0
    for i, b in enumerate(bossers):
        img = b.get('favorite_boss_img')
        boss = b.get('favorite_boss')
        print(f"{i+1}. {b['username']:<15} | Boss: {boss:<15} | Img: {img}")
        
        if img and 'pet_rock' not in img:
            found_custom += 1

    print(f"\nCustom Boss Images Found: {found_custom}/{len(bossers)}")

except Exception as e:
    print(f"Error: {e}")
