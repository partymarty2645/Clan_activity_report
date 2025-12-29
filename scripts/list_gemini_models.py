import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No API Key found")
    exit()

client = genai.Client(api_key=api_key)

print("Listing supported models:")
try:
    # Iterate over models using the new Client SDK
    for m in client.models.list():
        name = m.name.lower()
        # Filter: Only allow Gemini 2.5 Pro OR Gemini 3.x models
        if "gemini-2.5-pro" in name or "gemini-3" in name:
            print(f"- {m.name} ({m.display_name})")
except Exception as e:
    print(f"Error: {e}")
