import discord
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from core.config import Config
from core.timestamps import TimestampHelper
from database.connector import SessionLocal
from database.models import DiscordMessage

logger = logging.getLogger('DiscordService')

class DiscordFetcher:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.fetched_messages = []
        
        # Bind events
        self.client.event(self.on_ready)
        
        self.start_date = None
        self.end_date = None

        # Init complete

    async def fetch(self, start_date=None, end_date=None):
        self.start_date = start_date
        self.end_date = end_date
        logger.info(f"Starting Discord Fetch: {start_date} -> {end_date}")
        
        try:
            logger.info("Connecting to Discord...")
            if not Config.DISCORD_TOKEN:
                raise ValueError("Discord Token is missing from .env")
            await self.client.start(Config.DISCORD_TOKEN.strip())
        except Exception as e:
            logger.error(f"Discord Client Error: {e}")
        
        return len(self.fetched_messages)

    async def on_ready(self):
        logger.info(f'Logged in as {self.client.user}')
        try:
            # Dynamic Activity (Rec 4)
            await self.client.change_presence(activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name=f"{len(self.client.guilds)} Guilds | Harvesting..."
            ))
            await self._fetch_logic()
        finally:
            await self.client.close()

    async def _fetch_logic(self):
        channels = []
        if Config.RELAY_CHANNEL_ID:
            c = self.client.get_channel(int(Config.RELAY_CHANNEL_ID))
            if c: channels.append(c)
        else:
            for guild in self.client.guilds:
                channels.extend(guild.text_channels)
        
        import re
        relay_regex = re.compile(r"\*\*(.+?)\*\*:")
        
        db = SessionLocal()
        try:
            for channel in channels:
                logger.info(f"Scanning channel: {channel.name}")
                if not channel.permissions_for(channel.guild.me).read_message_history:
                    continue

                batch = []
                total_fetched = 0
                async for msg in channel.history(limit=None, after=self.start_date, oldest_first=True):
                    if self.end_date and msg.created_at > self.end_date:
                        break
                    
                    # Convert to Model
                    model = DiscordMessage(
                        id=msg.id,
                        author_id=msg.author.id,
                        author_name=msg.author.display_name, # Use Server Nickname (matches RSN better)
                        content=msg.content,
                        channel_id=msg.channel.id,
                        channel_name=msg.channel.name,
                        guild_id=msg.guild.id,
                        guild_name=msg.guild.name,
                        created_at=TimestampHelper.to_utc(msg.created_at)  # Ensure UTC
                    )
                    
                    # Relay Bot Parsing
                    if str(msg.author) == "Osrs clanchat#0000":
                        match = relay_regex.search(msg.content)
                        if match:
                            model.author_name = match.group(1).strip()

                    batch.append(model)
                    total_fetched += 1
                    # Optional per-run cap
                    if Config.DISCORD_MAX_MESSAGES and total_fetched >= Config.DISCORD_MAX_MESSAGES:
                        logger.warning(f"Reached DISCORD_MAX_MESSAGES cap ({Config.DISCORD_MAX_MESSAGES}). Stopping early.")
                        break
                    
                    if len(batch) >= Config.DISCORD_BATCH_SIZE:
                        self._save_batch(db, batch)
                        batch = []
                        await asyncio.sleep(Config.DISCORD_RATE_LIMIT_DELAY)

                if batch:
                    self._save_batch(db, batch)
        finally:
            db.close()

    def _save_batch(self, db, batch):
        try:
            for msg in batch:
                db.merge(msg) 
            db.commit()
            logger.info(f"Saved {len(batch)} messages.")
            # self.fetched_messages.extend(batch) # optimization: don't hold in memory
        except Exception as e:
            logger.error(f"DB Error: {e}")
            db.rollback()

    async def send_summary_embed(self, channel_id, stats):
        """
        Sends a rich embed summary of the report to the specified channel.
        stats: Dictionary of stats to display (e.g. {'Top XP': 'User (+5m)', ...})
        """
        if not Config.DISCORD_TOKEN: return
        
        try:
            await self.client.login(Config.DISCORD_TOKEN.strip())
            # We don't need full connection for this simple send if we use Rest, 
            # but using client is consistent.
            # actually client requires connect() for cache. 
            # Let's do a quick start/close or use REST if possible?
            # Creating a fresh client session is heavy. Ideally we'd keep it open.
            # For this architecture, we'll start, wait ready, send, close.
            
            logger.info(f"Sending Embed to Channel {channel_id}...")
            
            # Subclass Client to handle the one-off task
            class OneOffSender(discord.Client):
                async def on_ready(self):
                    try:
                        channel = self.get_channel(int(channel_id))
                        if channel:
                            embed = discord.Embed(
                                title="🏆 Clan Report Summary",
                                description=f"Report generated for **{datetime.now().strftime('%Y-%m-%d')}**",
                                color=Config.DISCORD_THEME_COLOR
                            )
                            
                            for k, v in stats.items():
                                embed.add_field(name=k, value=str(v), inline=True)
                                
                            embed.set_footer(text="Full report available (Excel)")
                            await channel.send(embed=embed)
                            logger.info("Embed sent successfully.")
                        else:
                            logger.error(f"Channel {channel_id} not found.")
                    except Exception as e:
                        logger.error(f"Failed to send embed: {e}")
                    finally:
                        await self.close()

            intents = discord.Intents.default()
            sender = OneOffSender(intents=intents)
            await sender.start(Config.DISCORD_TOKEN)
            
        except Exception as e:
            logger.error(f"Embed send failed: {e}")

discord_service = DiscordFetcher()

