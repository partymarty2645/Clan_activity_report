import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Use the key from the snippet if provided, or fallback to ENV
# The user provided a specific key in the snippet: "AIzaSyC56-jIlMX7VponH_1UEK-8LNMnMOEBRdY"
# I will use the ENV key to be safe/secure unless it fails, but the purpose might be to test THAT specific key?
# Actually, that key looks like a placeholder/example key from docs (often they look like AIzaSy...).
# I will stick to the project's ENV key to avoid leaking/using a potentially invalid example key.
# But I will use the MODEL and URL specified.

API_KEY = os.getenv("GEMINI_API_KEY")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

headers = {
    'Content-Type': 'application/json',
    'X-goog-api-key': API_KEY
}

data = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Explain how AI works in a few words"
                }
            ]
        }
    ]
}

print(f"Testing URL: {URL}")
try:
    response = requests.post(URL, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print("-" * 20)
    if response.status_code == 200:
        print("SUCCESS: gemini-2.0-flash is working.")
    else:
        print("FAILURE: Request failed.")
except Exception as e:
    print(f"Error: {e}")
