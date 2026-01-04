#!/usr/bin/env python
"""Quick verification of final AI insights."""
import json

data = json.load(open('data/ai_insights.json'))

print("✅ FINAL INSIGHTS SUMMARY")
print("=" * 70)
print(f"Total Insights: {len(data)}")

types_count = {}
for insight in data:
    itype = insight.get('type', 'unknown')
    types_count[itype] = types_count.get(itype, 0) + 1

print(f"\nType Distribution:")
for itype, count in sorted(types_count.items()):
    print(f"  - {itype}: {count}")

print("\n📊 Insights List:")
print("-" * 70)
for idx, insight in enumerate(data, 1):
    itype = insight.get('type', '?').upper()
    msg = insight.get('message', '')[:65]
    print(f"{idx:2d}. [{itype:12s}] {msg}")

print("\n✅ All insights loaded successfully!")
