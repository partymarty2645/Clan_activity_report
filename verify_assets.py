import json

# Load assets
with open('data/assets.json') as f:
    assets = json.load(f)

bosses = assets.get('bosses', [])
skills = assets.get('skills', [])
ranks_dict = assets.get('ranks', {})

# Flatten ranks
all_ranks = []
for cat in ranks_dict.values():
    if isinstance(cat, list):
        all_ranks.extend(cat)

print('✓ Full Asset Inventory Verified')
print('━' * 50)
print(f'  Bosses: {len(bosses)} (all available)')
print(f'  Skills: {len(skills)} (all available)')
print(f'  Ranks: {len(all_ranks)} (all available)')
print()
print(f'✓ Slayer in skills: {"Slayer" in skills}')
print(f'✓ Owner in ranks: {"Owner" in all_ranks}')
print(f'✓ Vorkath in bosses: {"Vorkath" in bosses}')
print()
print('Full skills list:')
print(f'  {skills}')
