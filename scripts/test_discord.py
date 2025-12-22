import os
import sys
import asyncio
import discord
from dotenv import load_dotenv

sys.path.append(os.getcwd())

# 1. Load manually to see raw value
load_dotenv(override=True)
raw_token = os.getenv("DISCORD_TOKEN", "")

print(f"Raw Token Length: {len(raw_token)}")
print(f"First 5 chars: '{raw_token[:5]}'")
print(f"Last 5 chars: '{raw_token[-5:]}'")

if not raw_token:
    print("ERROR: Token is empty!")
    sys.exit(1)

# 2. Test Connection
class TestClient(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.close()

async def main():
    intents = discord.Intents.default()
    client = TestClient(intents=intents)
    try:
        print("Attempting login...")
        await client.start(raw_token.strip()) # strip() to be safe
    except Exception as e:
        print(f"Login failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
