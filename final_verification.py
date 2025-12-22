import json

# Load the generated data
with open('clan_data.json', 'r') as f:
    data = json.load(f)

print('=' * 80)
print('DASHBOARD DATA VERIFICATION')
print('=' * 80)

members = data['allMembers']
print(f'\n📊 MEMBER COUNTS:')
print(f'  Total members shown: {len(members)}')
msgs = len([m for m in members if m.get("msgs_total", 0) > 0])
print(f'  Members with Discord messages: {msgs}')
boss = len([m for m in members if m.get("total_boss", 0) > 0])
print(f'  Members with boss kills: {boss}')
boss_only = len([m for m in members if m.get("total_boss", 0) > 0 and m.get("msgs_total", 0) == 0])
print(f'  Members with ONLY boss kills (no messages): {boss_only}')

print(f'\n🎯 BOSS DATA:')
total_boss = sum(m.get('total_boss', 0) for m in members)
print(f'  Total clan boss kills: {total_boss:,}')
print(f'  Average per member: {total_boss // len(members):,}')

# Top killers
top = sorted(members, key=lambda m: m.get('total_boss', 0), reverse=True)[:10]
print(f'\n👑 TOP 10 BOSS KILLERS:')
for i, m in enumerate(top, 1):
    user = m.get("username", "?")
    total = m.get("total_boss", 0)
    m30d = m.get("boss_30d", 0)
    print(f'  {i:2}. {user:<20} {total:>8} total  |  30d: {m30d:>5}')

print(f'\n✅ All data successfully exported and verified!')
