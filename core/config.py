import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    # Discord
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    RELAY_CHANNEL_ID = os.getenv('RELAY_CHANNEL_ID')
    DISCORD_BATCH_SIZE = int(os.getenv('DISCORD_BATCH_SIZE', 100))
    DISCORD_RATE_LIMIT_DELAY = float(os.getenv('DISCORD_RATE_LIMIT_DELAY', 0.75))
    DAYS_LOOKBACK = int(os.getenv('DAYS_LOOKBACK', 30))

    # WOM
    WOM_API_KEY = os.getenv('WOM_API_KEY')
    WOM_BASE_URL = os.getenv('WOM_BASE_URL', 'https://api.wiseoldman.net/v2')
    WOM_GROUP_ID = os.getenv('WOM_GROUP_ID', '11114')
    WOM_GROUP_SECRET = os.getenv('WOM_GROUP_SECRET')
    WOM_TARGET_RPM = int(os.getenv('WOM_TARGET_RPM', 90))
    WOM_RATE_LIMIT_DELAY = float(os.getenv('WOM_RATE_LIMIT_DELAY', 0.67))
    WOM_MAX_CONCURRENT = int(os.getenv('WOM_MAX_CONCURRENT', 2))
    
    # Testing
    TEST_MODE = os.getenv('WOM_TEST_MODE', 'False').lower() == 'true'
    TEST_LIMIT = int(os.getenv('WOM_TEST_LIMIT', 5))

    # Database
    DB_FILE = 'clan_data.db'
    
    # Report Settings
    OUTPUT_FILE_CSV = 'clan_report_summary_merged.csv'
    OUTPUT_FILE_XLSX = 'clan_report_summary_merged.xlsx'
    LOCAL_DRIVE_PATH = os.getenv('LOCAL_DRIVE_PATH')
    
    # Excel Styling
    EXCEL_ZERO_HIGHLIGHT = os.getenv('EXCEL_ZERO_HIGHLIGHT', 'true').lower() == 'true'
    EXCEL_ZERO_BG_COLOR = os.getenv('EXCEL_ZERO_BG_COLOR', '#FFC7CE')
    EXCEL_ZERO_FONT_COLOR = os.getenv('EXCEL_ZERO_FONT_COLOR', '#9C0006')
    
    # Aesthetics (User Verified Match)
    PROSPECTOR_COLOR = '#4bacc6' # Cyan
    DISCORD_THEME_COLOR = 0x4bacc6 
    EXCEL_DARK_MODE = True
    EXCEL_BG_COLOR = '#2b2b2b' # Base Dark
    EXCEL_FONT_COLOR = '#ffffff'
    
    # Column Group Colors (From Screenshot)
    # 1. Identity (User/Role) - Light Blue/Cornflower
    COLOR_IDENTITY = '#538dd5' 
    # 2. XP - Forest Green
    COLOR_XP = '#366e4a'
    # 3. Messages - Matching Blue
    COLOR_MESSAGES = '#538dd5'
    # 4. Boss - Darker Green/Olive
    COLOR_BOSS = '#3f634c'
    # 5. Questions - Blue
    COLOR_QUESTIONS = '#538dd5'
    # 6. Fav Word - Grey/Purple? (Keeping previous or default)
    COLOR_FAV_WORD = '#538dd5' 

    # Zero Values (Override)
    # The screenshot shows 0s have a specific Dark Grey BG + Red Text
    EXCEL_ZERO_HIGHLIGHT = True
    EXCEL_ZERO_BG_COLOR = '#262626' # Dark Grey (almost black)
    EXCEL_ZERO_FONT_COLOR = '#FF0000' # Red

    # Dates (Dynamic or Env)
    CUSTOM_START_DATE = os.getenv('CUSTOM_START_DATE', '2025-02-14')
