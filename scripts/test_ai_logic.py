
import sys
import os
import logging

# Add parent dir to path so we can import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_concepts import AIInsightGenerator

# Mock data
mock_members = [
    {'username': 'User1', 'total_xp': 50000000, 'xp_7d': 1000000, 'total_boss': 1000, 'boss_7d': 50, 'msgs_7d': 100, 'msgs_total': 5000, 'role': 'Admin', 'joined_at': '2020-01-01'},
    {'username': 'User2', 'total_xp': 100000, 'xp_7d': 50000, 'total_boss': 0, 'boss_7d': 0, 'msgs_7d': 10, 'msgs_total': 100, 'role': 'Member', 'joined_at': '2024-01-01'},
    {'username': 'User3', 'total_xp': 200000000, 'xp_7d': 0, 'total_boss': 5000, 'boss_7d': 0, 'msgs_7d': 0, 'msgs_total': 10000, 'role': 'Member', 'joined_at': '2021-01-01'},
    {'username': 'User4', 'total_xp': 1234567, 'xp_7d': 1234567, 'total_boss': 5, 'boss_7d': 5, 'msgs_7d': 500, 'msgs_total': 500, 'role': 'Recruit', 'joined_at': '2024-12-01'},
    {'username': 'User5', 'total_xp': 9000000, 'xp_7d': 500000, 'total_boss': 900, 'boss_7d': 50, 'msgs_7d': 20, 'msgs_total': 2000, 'role': 'Member', 'joined_at': '2022-01-01'},
]

def test_generation():
    print("Initializing Generator...")
    gen = AIInsightGenerator(mock_members)
    
    print("Generating Pool...")
    gen.generate_all()
    print(f"Pool size: {len(gen.pool)}")
    
    print("First 5 items:")
    for i in gen.pool[:5]:
        print(f" - {i['type']}: {i['message']}")
        
    print("-" * 20)
    print("Testing Selection (9 items)...")
    selection = gen.get_selection(9)
    print(f"Selected {len(selection)} items.")
    for item in selection:
        print(f" > {item['title']}: {item['message']}")

if __name__ == "__main__":
    test_generation()
