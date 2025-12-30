import os
import yaml
import logging
from typing import List, Tuple, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger("Config")

def load_yaml_config():
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    return {}

_yaml_config = load_yaml_config()

class Config:
    """
    Central Configuration.
    Precedence: Environment Variables > YAML Config > Defaults
    """
    
    # --- Paths ---
    DB_FILE = os.getenv('DB_FILE', 'clan_data.db')
    LOCAL_DRIVE_PATH = os.getenv('LOCAL_DRIVE_PATH', _yaml_config.get('drive_path'))

    # --- Discord ---
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    RELAY_CHANNEL_ID = os.getenv('RELAY_CHANNEL_ID')
    
    _d_conf = _yaml_config.get('discord', {})
    DISCORD_BATCH_SIZE = int(os.getenv('DISCORD_BATCH_SIZE', _d_conf.get('batch_size', 100)))
    DISCORD_RATE_LIMIT_DELAY = float(os.getenv('DISCORD_RATE_LIMIT_DELAY', _d_conf.get('rate_limit_delay', 0.75)))
    DISCORD_MAX_MESSAGES = int(os.getenv('DISCORD_MAX_MESSAGES', _d_conf.get('max_messages', 0))) # 0 = Unlimited
    DAYS_LOOKBACK = int(os.getenv('DAYS_LOOKBACK', 400)) 

    # --- WOM ---
    WOM_API_KEY = os.getenv('WOM_API_KEY')
    WOM_GROUP_ID = os.getenv('WOM_GROUP_ID', '11114')
    WOM_GROUP_SECRET = os.getenv('WOM_GROUP_SECRET')
    WOM_BASE_URL = os.getenv('WOM_BASE_URL', 'https://api.wiseoldman.net/v2')
    
    # --- AI Keys ---
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    _w_conf = _yaml_config.get('wom', {})
    WOM_TARGET_RPM = int(os.getenv('WOM_TARGET_RPM', _w_conf.get('target_rpm', 90)))
    WOM_RATE_LIMIT_DELAY = float(os.getenv('WOM_RATE_LIMIT_DELAY', _w_conf.get('rate_limit_delay', 0.67)))
    WOM_MAX_CONCURRENT = int(os.getenv('WOM_MAX_CONCURRENT', _w_conf.get('max_concurrent', 2)))
    # Short update delay: If true, wait 10s after triggering update. If false, wait 3 minutes (180s).
    WOM_SHORT_UPDATE_DELAY = str(os.getenv('WOM_SHORT_UPDATE_DELAY', _w_conf.get('short_update_delay', False))).lower() == 'true'
    WOM_UPDATE_WAIT = int(os.getenv('WOM_UPDATE_WAIT', 10 if WOM_SHORT_UPDATE_DELAY else 180))
    
    # --- Reporting ---
    OUTPUT_FILE_XLSX = 'clan_report_summary_merged.xlsx'
    CUSTOM_START_DATE = os.getenv('CUSTOM_START_DATE', '2025-02-14')
    
    _report_conf = _yaml_config.get('report', {})
    ROLE_WEIGHTS = _report_conf.get('role_weights', {
        'owner': 100, 'deputy_owner': 90, 'zenyte': 80, 'dragonstone': 80,
        'administrator': 70, 'saviour': 60, 'prospector': 10, 'guest': 0
    })

    # --- Analysis / Logic Constants ---
    LEADERBOARD_WEIGHT_BOSS = int(os.getenv('LEADERBOARD_WEIGHT_BOSS', 3))
    LEADERBOARD_WEIGHT_MSGS = int(os.getenv('LEADERBOARD_WEIGHT_MSGS', 6))
    
    # Purge Thresholds (Defaults set to 0 as requested)
    PURGE_THRESHOLD_DAYS = int(os.getenv('PURGE_THRESHOLD_DAYS', 60))
    PURGE_MIN_XP = int(os.getenv('PURGE_MIN_XP', 0))
    PURGE_MIN_BOSS = int(os.getenv('PURGE_MIN_BOSS', 0))
    PURGE_MIN_MSGS = int(os.getenv('PURGE_MIN_MSGS', 0)) # Was "Ghost Msg Count"

    # Harvest Safety
    HARVEST_STALE_THRESHOLD_SECONDS = int(os.getenv('HARVEST_STALE_THRESHOLD_SECONDS', 86400))
    HARVEST_SAFE_DELETE_RATIO = float(os.getenv('HARVEST_SAFE_DELETE_RATIO', 0.20))
    
    # WOM Snapshot Staleness Optimization (skip fetching players with recent data)
    # Set to 0 to disable staleness skipping (fetch all players every run)
    # Set to desired hours threshold (e.g., 6 = skip players with snapshots < 6 hours old)
    WOM_STALENESS_SKIP_HOURS = int(os.getenv('WOM_STALENESS_SKIP_HOURS', 6))

    # Dashboard Limits
    LEADERBOARD_SIZE = int(os.getenv('LEADERBOARD_SIZE', 10))
    TOP_BOSS_CARDS = int(os.getenv('TOP_BOSS_CARDS', 4))
    
    # --- Key Dates ---
    # Parse CUSTOM_START_DATE or default
    try:
        _yr, _mo, _dy = map(int, CUSTOM_START_DATE.split('-'))
        CLAN_FOUNDING_DATE = datetime(_yr, _mo, _dy, tzinfo=timezone.utc)
    except:
        CLAN_FOUNDING_DATE = datetime(2025, 2, 14, tzinfo=timezone.utc)

    # --- Aesthetics ---
    _aesthetics = _report_conf.get('aesthetics', {})
    _cols = _aesthetics.get('column_colors', {})
    _zeros = _aesthetics.get('zero_values', {})

    PROSPECTOR_COLOR = _aesthetics.get('prospector_color', '#4bacc6')
    EXCEL_DARK_MODE = _aesthetics.get('excel_dark_mode', True)
    EXCEL_BG_COLOR = _aesthetics.get('excel_bg_color', '#2b2b2b')
    EXCEL_FONT_COLOR = _aesthetics.get('excel_font_color', '#ffffff')
    
    COLOR_IDENTITY = _cols.get('identity', '#538dd5')
    COLOR_XP = _cols.get('xp', '#366e4a')
    COLOR_MESSAGES = _cols.get('messages', '#538dd5')
    COLOR_BOSS = _cols.get('boss', '#3f634c')
    
    EXCEL_ZERO_HIGHLIGHT = _zeros.get('highlight', True)
    EXCEL_ZERO_BG_COLOR = _zeros.get('bg_color', '#262626')
    EXCEL_ZERO_FONT_COLOR = _zeros.get('font_color', '#FF0000')

    @staticmethod
    def validate() -> Tuple[bool, List[str]]:
        """
        Validate all critical configuration values.
        
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
            - is_valid=True if all critical config values are present
            - errors contains list of missing/invalid values
        """
        errors = []
        
        # Critical API Keys
        if not Config.WOM_API_KEY or Config.WOM_API_KEY.strip() == '':
            errors.append("WOM_API_KEY is missing or empty")
        
        if not Config.DISCORD_TOKEN or Config.DISCORD_TOKEN.strip() == '':
            errors.append("DISCORD_TOKEN is missing or empty")
        
        # Critical IDs
        if not Config.WOM_GROUP_ID:
            errors.append("WOM_GROUP_ID is missing")
        
        if not Config.RELAY_CHANNEL_ID:
            errors.append("RELAY_CHANNEL_ID is missing")
        
        # Optional but important
        if not Config.WOM_GROUP_SECRET or Config.WOM_GROUP_SECRET.strip() == '':
            logger.warning("WOM_GROUP_SECRET is not set (some operations may be limited)")
        
        if not Config.DB_FILE:
            errors.append("DB_FILE is missing")
        
        return (len(errors) == 0, errors)
    
    @staticmethod
    def fail_fast() -> None:
        """
        Fail fast if configuration is invalid.
        
        Raises:
            ValueError: If any critical configuration is missing
        """
        is_valid, errors = Config.validate()
        
        if not is_valid:
            error_msg = "Configuration invalid:\n" + "\n".join([f"  - {err}" for err in errors])
            error_msg += "\n\nPlease check your .env file or config.yaml"
            raise ValueError(error_msg)
    
    @staticmethod
    def log_config() -> None:
        """Log all loaded configuration values (with sensitive values redacted)."""
        logger.info("=" * 60)
        logger.info("Configuration Loaded")
        logger.info("=" * 60)
        logger.info(f"Database: {Config.DB_FILE}")
        logger.info(f"WOM Group ID: {Config.WOM_GROUP_ID}")
        logger.info(f"Discord Token: {'***' if Config.DISCORD_TOKEN else 'NOT SET'}")
        logger.info(f"WOM API Key: {'***' if Config.WOM_API_KEY else 'NOT SET'}")
        logger.info(f"Discord Relay Channel: {Config.RELAY_CHANNEL_ID}")
        logger.info(f"Days Lookback: {Config.DAYS_LOOKBACK}")
        logger.info(f"Discord Batch Size: {Config.DISCORD_BATCH_SIZE}")
        logger.info(f"WOM Rate Limit: {Config.WOM_RATE_LIMIT_DELAY}s delay, {Config.WOM_TARGET_RPM} RPM target")
        logger.info("=" * 60)
