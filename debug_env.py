from dotenv import load_dotenv
import os

print("--- Debug Env ---")
load_dotenv()
raw = os.getenv('WOM_TEST_MODE')
print(f"Raw WOM_TEST_MODE: '{raw}'")
print(f"Type: {type(raw)}")
is_true = str(raw).lower() == 'true'
print(f"Evaluates to True? {is_true}")
