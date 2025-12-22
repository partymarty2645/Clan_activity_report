import json
data = json.load(open('clan_data.json'))
members = data['allMembers']
print(f'Total members: {len(members)}')
print(f'Total boss kills: {sum(m.get("total_boss", 0) for m in members)}')

# Find members with boss kills but 0 messages
boss_only = [m for m in members if m.get('total_boss', 0) > 0 and m.get('msgs_total', 0) == 0]
print(f'Boss-only members (no discord messages): {len(boss_only)}')

# Check sample
if boss_only:
    print(f'\nSample boss-only members:')
    for m in boss_only[:3]:
        print(f'  - {m.get("username", m.get("name"))} (Boss: {m.get("total_boss", 0)}, Msgs: {m.get("msgs_total", 0)})')
