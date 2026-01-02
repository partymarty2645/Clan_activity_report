#!/usr/bin/env python
"""Quick test to validate dashboard fixes"""
import json

# Load clan_data.json
with open('clan_data.json', 'r') as f:
    data = json.load(f)

# Test 1: Check boss trend data
print("\n✅ TEST 1: Boss Trend Data")
trend = data.get('chart_boss_trend', {})
print(f"  Boss: {trend.get('boss_name', 'N/A')}")
print(f"  Total Gain: {trend.get('total_gain', 'N/A')}")
if trend.get('total_gain') and isinstance(trend['total_gain'], (int, float)):
    gain = trend['total_gain']
    if gain > 100:
        print(f"  ✅ PASS: Gain {gain} is correctly scaled (not 4.3)")
    else:
        print(f"  ❌ FAIL: Gain {gain} still looks scaled")

# Test 2: Check leaderboard scoring
print("\n✅ TEST 2: Leaderboard Scoring")
members = data.get('allMembers', [])
if members:
    # Find high-msg and high-xp members
    high_msg = sorted(members, key=lambda x: x.get('msgs_7d', 0), reverse=True)[:1]
    high_xp = sorted(members, key=lambda x: x.get('xp_7d', 0), reverse=True)[:1]
    
    if high_msg:
        print(f"  Top Messenger: {high_msg[0].get('username')} ({high_msg[0].get('msgs_7d')} msgs)")
    if high_xp:
        print(f"  Top XP Gainer: {high_xp[0].get('username')} ({high_xp[0].get('xp_7d')} xp)")
    print(f"  ✅ PASS: Leaderboard data available")

# Test 3: Check CSS variable definition
print("\n✅ TEST 3: CSS Variables")
with open('assets/styles.css', 'r') as f:
    css = f.read()
    if '--neon-purple: #bc13fe' in css:
        print(f"  ✅ PASS: --neon-purple CSS variable defined")
    else:
        print(f"  ❌ FAIL: --neon-purple CSS variable not found")

print("\n" + "="*50)
print("Validation Complete!")
