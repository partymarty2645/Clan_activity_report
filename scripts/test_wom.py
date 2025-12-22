import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Load env directly
load_dotenv(override=True)
API_KEY = os.getenv("WOM_API_KEY")
GROUP_ID = os.getenv("WOM_GROUP_ID", "11114")
BASE_URL = "https://api.wiseoldman.net/v2"

headers = {
    'User-Agent': 'NevrLucky (Contact: partymarty94)',
    'x-api-key': API_KEY,
    'Content-Type': 'application/json'
}

async def test_wom():
    print(f"Testing WOM API...")
    print(f"URL: {BASE_URL}/groups/{GROUP_ID}")
    print(f"Headers: User-Agent={headers['User-Agent']}, x-api-key={headers['x-api-key'][:5]}...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/groups/{GROUP_ID}", headers=headers) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                print(f"Response: {text[:200]}...") # Print first 200 chars
                
                if resp.status == 200:
                    print("SUCCESS: API is reachable.")
                else:
                    print("FAILURE: API returned error.")
        except Exception as e:
            print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    asyncio.run(test_wom())
