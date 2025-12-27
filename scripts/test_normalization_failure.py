import sys
import os
sys.path.append(os.getcwd())
from core.usernames import UsernameNormalizer

def test_failure():
    # Scenario: Distinct OSRS accounts that collide under current logic
    user1 = "Noob Man"       # Valid OSRS name
    user2 = "NoobMan"        # Valid OSRS name (Distinct!)
    
    norm1 = UsernameNormalizer.normalize(user1)
    norm2 = UsernameNormalizer.normalize(user2)
    
    print(f"User 1: '{user1}' -> Normalized: '{norm1}'")
    print(f"User 2: '{user2}' -> Normalized: '{norm2}'")
    
    if norm1 == norm2:
        print("❌ FAILURE: Distinct users normalized to SAME string!")
        print("This means 'Noob Man' and 'NoobMan' are treated as duplicates.")
    else:
        print("✅ SUCCESS: Users are distinct.")

    # Scenario 2: Underscores vs Spaces (Should be same)
    user3 = "Iron_Man_123"
    user4 = "Iron Man 123"
    
    norm3 = UsernameNormalizer.normalize(user3)
    norm4 = UsernameNormalizer.normalize(user4)
    
    print(f"\nUser 3: '{user3}' -> Normalized: '{norm3}'")
    print(f"User 4: '{user4}' -> Normalized: '{norm4}'")
    
    if norm3 == norm4:
        print("✅ Correct: Underscores and spaces are treated equivalently.")
    else:
        print("❌ Failure: Underscores vs Spaces mismatch.")

if __name__ == "__main__":
    test_failure()
