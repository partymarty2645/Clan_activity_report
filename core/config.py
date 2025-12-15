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
    # --- Discord ---
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    RELAY_CHANNEL_ID = os.getenv('RELAY_CHANNEL_ID')
    
    _d_conf = _yaml_config.get('discord', {})
    DISCORD_BATCH_SIZE = int(os.getenv('DISCORD_BATCH_SIZE', _d_conf.get('batch_size', 100)))
    DISCORD_RATE_LIMIT_DELAY = float(os.getenv('DISCORD_RATE_LIMIT_DELAY', _d_conf.get('rate_limit_delay', 0.75)))
    DAYS_LOOKBACK = int(os.getenv('DAYS_LOOKBACK', 30))

    # --- WOM ---
    WOM_API_KEY = os.getenv('WOM_API_KEY')
    WOM_BASE_URL = os.getenv('WOM_BASE_URL', 'https://api.wiseoldman.net/v2')
    WOM_GROUP_ID = os.getenv('WOM_GROUP_ID', '11114')
    WOM_GROUP_SECRET = os.getenv('WOM_GROUP_SECRET')
    
    _w_conf = _yaml_config.get('wom', {})
    WOM_TARGET_RPM = int(os.getenv('WOM_TARGET_RPM', _w_conf.get('target_rpm', 90)))
    WOM_RATE_LIMIT_DELAY = float(os.getenv('WOM_RATE_LIMIT_DELAY', _w_conf.get('rate_limit_delay', 0.67)))
    WOM_MAX_CONCURRENT = int(os.getenv('WOM_MAX_CONCURRENT', _w_conf.get('max_concurrent', 2)))
    WOM_SHORT_UPDATE_DELAY = os.getenv('WOM_SHORT_UPDATE_DELAY', str(_w_conf.get('short_update_delay', True))).lower() == 'true'
    WOM_DEEP_SCAN = os.getenv('WOM_DEEP_SCAN', 'False').lower() == 'true'
    
    # --- Testing ---
    TEST_MODE = os.getenv('WOM_TEST_MODE', 'False').lower() == 'true'
    TEST_LIMIT = int(os.getenv('WOM_TEST_LIMIT', 5))

    # --- Database ---
    DB_FILE = 'clan_data.db'
    
    # --- Report Settings ---
    OUTPUT_FILE_CSV = 'clan_report_summary_merged.csv'
    OUTPUT_FILE_XLSX = 'clan_report_summary_merged.xlsx'
    LOCAL_DRIVE_PATH = os.getenv('LOCAL_DRIVE_PATH')
    CUSTOM_START_DATE = os.getenv('CUSTOM_START_DATE', '2025-02-14')
    
    # --- Aesthetics (Loaded from YAML) ---
    _aesthetics = _yaml_config.get('report', {}).get('aesthetics', {})
    _cols = _aesthetics.get('column_colors', {})
    _zeros = _aesthetics.get('zero_values', {})

    PROSPECTOR_COLOR = _aesthetics.get('prospector_color', '#4bacc6')
    DISCORD_THEME_COLOR = int(_aesthetics.get('prospector_color', '#4bacc6').replace('#',''), 16)
    EXCEL_DARK_MODE = _aesthetics.get('excel_dark_mode', True)
    EXCEL_BG_COLOR = _aesthetics.get('excel_bg_color', '#2b2b2b')
    EXCEL_FONT_COLOR = _aesthetics.get('excel_font_color', '#ffffff')
    
    COLOR_IDENTITY = _cols.get('identity', '#538dd5')
    COLOR_XP = _cols.get('xp', '#366e4a')
    COLOR_MESSAGES = _cols.get('messages', '#538dd5')
    COLOR_BOSS = _cols.get('boss', '#3f634c')
    COLOR_QUESTIONS = _cols.get('questions', '#538dd5')
    COLOR_FAV_WORD = _cols.get('fav_word', '#538dd5')

    EXCEL_ZERO_HIGHLIGHT = _zeros.get('highlight', True)
    EXCEL_ZERO_BG_COLOR = _zeros.get('bg_color', '#262626')
    EXCEL_ZERO_FONT_COLOR = _zeros.get('font_color', '#FF0000')

    # --- Logic ---
    ROLE_WEIGHTS = _yaml_config.get('report', {}).get('role_weights', {
        'owner': 100, 'deputy_owner': 90, 'zenyte': 80, 'dragonstone': 80,
        'administrator': 70, 'saviour': 60, 'prospector': 10, 'guest': 0
    })
