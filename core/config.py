import os
import yaml
from dotenv import load_dotenv

load_dotenv(override=True)

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
    
    _w_conf = _yaml_config.get('wom', {})
    WOM_TARGET_RPM = int(os.getenv('WOM_TARGET_RPM', _w_conf.get('target_rpm', 90)))
    WOM_RATE_LIMIT_DELAY = float(os.getenv('WOM_RATE_LIMIT_DELAY', _w_conf.get('rate_limit_delay', 0.67)))
    WOM_MAX_CONCURRENT = int(os.getenv('WOM_MAX_CONCURRENT', _w_conf.get('max_concurrent', 2)))
    # Short update delay: If true, wait 10s after triggering update. If false, wait 5 min (300s).
    WOM_SHORT_UPDATE_DELAY = str(os.getenv('WOM_SHORT_UPDATE_DELAY', _w_conf.get('short_update_delay', True))).lower() == 'true'
    WOM_UPDATE_WAIT = int(os.getenv('WOM_UPDATE_WAIT', 10 if WOM_SHORT_UPDATE_DELAY else 300))
    
    # --- Reporting ---
    OUTPUT_FILE_XLSX = 'clan_report_summary_merged.xlsx'
    CUSTOM_START_DATE = os.getenv('CUSTOM_START_DATE', '2025-02-14')
    
    _report_conf = _yaml_config.get('report', {})
    ROLE_WEIGHTS = _report_conf.get('role_weights', {
        'owner': 100, 'deputy_owner': 90, 'zenyte': 80, 'dragonstone': 80,
        'administrator': 70, 'saviour': 60, 'prospector': 10, 'guest': 0
    })

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
