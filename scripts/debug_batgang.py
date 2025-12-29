from core.usernames import UsernameNormalizer

names = [
    "Mr Batgang",
    "mrbatgang",
    "MrBatGang",
    "Mr  Batgang",
    "Mr_Batgang"
]

print("--- Normalization Test ---")
for n in names:
    norm = UsernameNormalizer.normalize(n)
    print(f"'{n}' -> '{norm}'")

print("\n--- Comparison Test ---")
ref = "mrbatgang"
for n in names:
    is_match = UsernameNormalizer.are_same_user(n, ref)
    print(f"'{n}' == '{ref}'? {is_match}")
