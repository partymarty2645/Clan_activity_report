import discord
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import database  # For incremental message saves

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("Error: DISCORD_TOKEN not found in .env file.")
    exit(1)

# standard intents
intents = discord.Intents.default()
intents.message_content = True 

client = discord.Client(intents=intents)

days_lookback_env = int(os.getenv('DAYS_LOOKBACK', 30))
OUTPUT_FILE = f'discord_messages_{days_lookback_env}days.json'
BATCH_SIZE = 100
RATE_LIMIT_DELAY = float(os.getenv('DISCORD_RATE_LIMIT_DELAY', 0.75))  # 1.33 req/s baseline (avoids 429s, adaptive adjusts)
DISCORD_429_WAIT = 15.0  # Wait time on 429 rate limit

# Adaptive rate limiting state
_rate_limit_hits = []  # Track 429s
_current_delay = RATE_LIMIT_DELAY  # Current adaptive delay

def save_data(data):
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving data: {e}")

def adjust_discord_rate_limit():
    """Adaptively adjust Discord rate limit based on 429 hits."""
    global _current_delay, _rate_limit_hits
    
    now = datetime.now().timestamp()
    # Clean old hits (>5 minutes)
    _rate_limit_hits = [t for t in _rate_limit_hits if now - t < 300]
    
    if len(_rate_limit_hits) > 2:  # Multiple 429s recently
        # Slow down: increase delay by 30%
        _current_delay *= 1.3
        print(f"[Discord] ⚠️ Adaptive rate limit: Slowing to {_current_delay:.2f}s delay")
    elif len(_rate_limit_hits) == 0 and _current_delay > RATE_LIMIT_DELAY:
        # Speed up: decrease delay by 15% if no recent 429s
        _current_delay = max(_current_delay * 0.85, RATE_LIMIT_DELAY)
        print(f"[Discord] ⚡ Adaptive rate limit: Speeding up to {_current_delay:.2f}s delay")

# Global variable to store results
fetched_messages = []

# Signal to stop the bot
stop_signal = asyncio.Event()

@client.event
async def on_ready():
    if getattr(client, 'fetch_done', False):
        return

    print(f'Logged in as {client.user}')
    try:
        # Retrieve dates stored on the client instance
        start = getattr(client, 'fetch_start_date', None)
        end = getattr(client, 'fetch_end_date', None)
        await fetch_messages_logic(start, end)
        client.fetch_done = True
    finally:
        await client.close()


async def fetch_messages_logic(start_date=None, end_date=None):
    global fetched_messages
    
    # If dates aren't provided, fall back to environment variable logic (or default)
    if not start_date:
        days_lookback = int(os.getenv('DAYS_LOOKBACK', 30))
        start_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
        print(f"No start date provided. Using default lookback: {days_lookback} days.")

    # Ensure dates are timezone-aware (UTC)
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    print(f"Fetching messages from {start_date} to {end_date or 'Now'}")
    
    current_after = start_date
    
    all_messages = []
    
    try:
        RELAY_CHANNEL_ID = os.getenv('RELAY_CHANNEL_ID')

        channels_to_scan = []
        if RELAY_CHANNEL_ID:
            print(f"Fetching only from configured channel ID: {RELAY_CHANNEL_ID}")
            channel = client.get_channel(int(RELAY_CHANNEL_ID))
            if not channel:
                print(f"Error: Channel {RELAY_CHANNEL_ID} not found/accessible.")
            else:
                channels_to_scan = [channel]
        else:
            print("No RELAY_CHANNEL_ID configured. Scanning all text channels.")
            # Gather all text channels from all guilds
            for guild in client.guilds:
                channels_to_scan.extend(guild.text_channels)

        for channel in channels_to_scan:
            guild = channel.guild
            print(f"Scanning channel: {channel.name} in {guild.name}")
            try:
                    permissions = channel.permissions_for(guild.me)
                    if not permissions.read_message_history:
                        print(f"  Skipping {channel.name} (no history permission)")
                        continue

                    print(f"  Fetching from {channel.name}...")
                    channel_msg_count = 0
                    current_after = start_date
                    
                    while True:
                        # Fetch a batch
                        batch = []
                        try:
                            async for msg in channel.history(limit=BATCH_SIZE, after=current_after, oldest_first=True):
                                batch.append(msg)
                        except discord.errors.RateLimited as e:
                            # Handle 429 rate limit
                            global _rate_limit_hits, _current_delay
                            _rate_limit_hits.append(datetime.now().timestamp())
                            adjust_discord_rate_limit()
                            wait_time = DISCORD_429_WAIT
                            print(f"\n[Discord] 🛑 RATE LIMIT HIT (429)! Waiting {wait_time}s... ({channel.name})\n")
                            await asyncio.sleep(wait_time)
                            continue
                        except discord.Forbidden:
                            print(f"    Forbidden to read history of {channel.name}")
                            break
                        except Exception as e:
                            print(f"    Error reading history of {channel.name}: {e}")
                            break
                        
                        if not batch:
                            break # No more messages
                            
                        # Process batch
                        for message in batch:
                            # Filter by end_date if provided
                            # Note: messages are fetched oldest_first. 
                            # If we hit a message > end_date, we can stop fetching THIS channel completely?
                            # Not necessarily, because 'batch' might contain a mix if boundary is within batch.
                            # But since we fetch 'after', time increases.
                            if end_date and message.created_at > end_date:
                                print(f"    Reached end date limit ({end_date}). Stopping fetch for {channel.name}.")
                                # We can stop processing this channel entirely
                                should_stop_channel = True
                                break

                            msg_data = {
                                'id': message.id,
                                'content': message.content,
                                'author_id': message.author.id,
                                'author_name': str(message.author),
                                'created_at': message.created_at.isoformat(),
                                'channel_id': message.channel.id,
                                'channel_name': message.channel.name,
                                'guild_id': message.guild.id,
                                'guild_name': message.guild.name
                            }
                            all_messages.append(msg_data)
                        
                        if 'should_stop_channel' in locals() and should_stop_channel:
                            break
                        
                        # Incremental database save every 1000 messages (batch insert and clear)
                        if len(all_messages) >= 1000:
                            count, skipped = database.insert_messages(all_messages)
                            print(f"    [💾 DB Save] Inserted {count} messages, {skipped} duplicates skipped. Clearing memory.")
                            all_messages.clear()  # Clear to avoid re-inserting
                        
                        channel_msg_count += len(batch)
                        # Optimization: Use the Message object itself for 'after' pagination
                        # This uses the Message ID, which avoids data loss from timestamp collisions.
                        current_after = batch[-1]
                        
                        # --- RPS & Timeline Calculation ---
                        now_time = datetime.now().timestamp()
                        elapsed = now_time - getattr(client, 'fetch_start_time', now_time)
                        req_count = getattr(client, 'request_count', 0) + 1
                        client.request_count = req_count
                        
                        rps = req_count / elapsed if elapsed > 0 else 0
                        
                        t_start = batch[0].created_at.strftime('%Y-%m-%d %H:%M')
                        t_end = batch[-1].created_at.strftime('%Y-%m-%d %H:%M')
                        
                        print(f"    [Progress] {channel.name}: fetched {len(batch)} new (Total: {channel_msg_count}).")
                        print(f"      [Discord] Batch Timeline: {t_start} -> {t_end}")
                        print(f"      [RPS: {rps:.2f}]")
                        
                        # Adaptive rate limit sleep
                        global _current_delay
                        await asyncio.sleep(_current_delay)
                        
                        # Periodically adjust if no recent 429s
                        if channel_msg_count % 500 == 0:
                            adjust_discord_rate_limit()
                        
                        if len(batch) < BATCH_SIZE:
                            break

                    print(f"    Finished {channel.name}. Total found: {channel_msg_count}.")
                    
            except Exception as e:
                print(f"    Error in {channel.name}: {e}")
        
        # Final save of remaining messages (< 1000)
        if all_messages:
            count, skipped = database.insert_messages(all_messages)
            print(f"    [💾 Final DB Save] Inserted {count} messages, {skipped} duplicates skipped.")
        
        fetched_messages = all_messages
        save_data(all_messages)
        print(f"Done! All messages saved to database.")
    except Exception as e:
        print(f"Global error during fetch: {e}")
        # Save any partial progress on error
        if all_messages:
            count, skipped = database.insert_messages(all_messages)
            print(f"    [💾 Emergency Save] Inserted {count} messages before crash.")

async def run_discord_fetch(start_date=None, end_date=None):
    """Async call to run the bot and return messages."""
    global fetched_messages
    fetched_messages = [] # Reset
    
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found.")
        return []

    try:
        # Store params on client so on_ready can access them
        client.fetch_start_date = start_date
        client.fetch_end_date = end_date
        client.fetch_start_time = datetime.now().timestamp()
        client.request_count = 0
        
        # discord.Client.start is valid for running within an existing loop
        # We start the bot, it logs in, on_ready triggers fetch_messages_logic, which eventually closes the client.
        await client.start(TOKEN)
    except Exception as e:
        print(f"Error running bot: {e}")
        
    return fetched_messages

if __name__ == '__main__':
    asyncio.run(run_discord_fetch())
