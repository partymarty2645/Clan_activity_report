import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

print("Fetching available models...")
try:
    # Use the new SDK's method to list models, if available, or fallback
    # The new SDK documentation suggests client.models.list()
    for m in client.models.list():
        if "gemini" in m.name:
            print(f"- {m.name} ({m.display_name})")
except Exception as e:
    print(f"Error listing models: {e}")
