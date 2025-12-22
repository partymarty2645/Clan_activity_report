import json
with open('clan_data.json', 'r') as f:
    data = json.load(f)

print('JSON Export Summary:')
print(f'  Total members in allMembers: {len(data["allMembers"])}')
print(f'  Total clan boss kills: {sum(m.get("total_boss", 0) for m in data["allMembers"])}')

# Find members with boss kills but 0 messages
boss_only = [m for m in data['allMembers'] if m.get('total_boss', 0) > 0 and m.get('msgs_total', 0) == 0]
print(f'  Members with ONLY boss kills (0 messages): {len(boss_only)}')
if boss_only:
    print(f'    Examples:')
    for m in boss_only[:5]:
        print(f'      - {m["name"]} ({m["total_boss"]} total boss kills)')

# Show top 5
top = sorted(data['allMembers'], key=lambda m: m.get('total_boss', 0), reverse=True)[:5]
print(f'\n  Top 5 Boss Killers (All Data):')
for m in top:
    print(f'    {m["name"]:<20} Total: {m.get("total_boss", 0):>7} Msgs: {m.get("msgs_total", 0):>6}')
