
"""
styles.py
=========
Defines the visual theme and format dictionaries for the Excel report.
Pull values from Core Config (YAML-loaded) to allow dynamic aesthetics.
"""
from core.config import Config

class Theme:
    # DYNAMIC PALETTE (Loaded from Config)
    # Fallbacks provided if Config is missing specific keys
    
    # Primary Identity
    GOLD = Config.COLOR_IDENTITY if Config.COLOR_IDENTITY else '#FFD700'
    GOLD_BOLD = '#FFA500' # Deep Orange-ish Gold for extra pop
    
    # Neon Accents
    RED_NEON = Config.COLOR_BOSS if Config.COLOR_BOSS else '#FF3333'
    GREEN_NEON = Config.COLOR_XP if Config.COLOR_XP else '#33FF33'
    BLUE_NEON = Config.COLOR_MESSAGES if Config.COLOR_MESSAGES else '#33CCFF'
    CYAN_NEON = '#00FFFF' # Specific Cyan for messages if needed
    
    # Backgrounds
    BG_BLACK = Config.EXCEL_BG_COLOR if Config.EXCEL_BG_COLOR else '#050505'
    BG_DARK = '#1a1a1a'
    BG_CARD = '#121212' # Darker cards
    BG_HEADER = '#000000'
    
    # TEXT
    TEXT_WHITE = Config.EXCEL_FONT_COLOR if Config.EXCEL_FONT_COLOR else '#E0E0E0'
    TEXT_GOLD = GOLD
    
    # BORDERS
    BORDER_GREY = '#222222'
    BORDER_GOLD = GOLD
    BORDER_NEON = '#33FF33' # Default neon border

class ExcelFormats:
    """
    Helper to generate XlsxWriter format dictionaries.
    """
    
    @staticmethod
    def base(workbook):
        return {
            'font_name': 'Inter', # Modern look
            'font_size': 10,
            'font_color': Theme.TEXT_WHITE,
            'bg_color': Theme.BG_BLACK,
            'border': 1,
            'border_color': Theme.BORDER_GREY,
            'valign': 'vcenter'
        }

    @staticmethod
    def header(workbook):
        return {
            'bold': True,
            'font_color': Theme.GOLD_BOLD,
            'bg_color': Theme.BG_HEADER,
            'border': 1,
            'border_color': Theme.GOLD,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12
        }

    @staticmethod
    def neon_header(workbook):
        """Bold Gold headers with a dark neon vibe"""
        return {
            'bold': True,
            'font_color': '#FFFA00', # Electric Gold
            'bg_color': '#000000',
            'border': 2,
            'top_color': '#FFFA00',
            'bottom_color': '#FFFA00',
            'left_color': '#FFFA00',
            'right_color': '#FFFA00',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 13,
            'font_name': 'Cinzel' # OSRS-like font if available, fallback to Serif
        }

    @staticmethod
    def dashboard_card_header(workbook, text_color=None):
        color = text_color if text_color else Theme.TEXT_GOLD
        return {
            'bold': True,
            'font_color': color,
            'bg_color': Theme.BG_CARD,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
            'border': 1,
            'top_color': color,
            'bottom_color': color,
            'left_color': color,
            'right_color': color
        }

    @staticmethod
    def dashboard_card_value(workbook, text_color=None):
        color = text_color if text_color else Theme.BORDER_GOLD
        return {
            'bold': True,
            'font_color': '#FFFFFF',
            'bg_color': Theme.BG_CARD,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 20,
            'border': 1,
            'top_color': color,
            'bottom_color': color,
            'left_color': color,
            'right_color': color
        }

    @staticmethod
    def number_large(workbook):
        # 1.5M, 250.0K
        return '[>=1000000]#,##0.0,,"M";[>=1000]#,##0.0,"K";0'

    @staticmethod
    def launch_button(workbook, color=Theme.RED_NEON):
        return {
            'bold': True,
            'font_color': '#FFFFFF',
            'bg_color': color,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16,
            'border': 3,
            'top_color': '#FFFFFF',
            'bottom_color': '#FFFFFF',
            'left_color': '#FFFFFF',
            'right_color': '#FFFFFF',
            'font_name': 'Impact'
        }

    @staticmethod
    def neon_button(workbook, color='#00FF00'):
        """Specific neon buttons with glow effect (border)"""
        return {
            'bold': True,
            'font_color': '#000000',
            'bg_color': color,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
            'border': 2,
            'top_color': '#FFFFFF',
            'bottom_color': '#FFFFFF',
            'left_color': '#FFFFFF',
            'right_color': '#FFFFFF'
        }

    @staticmethod
    def rank_gold(workbook):
        return {
            'bg_color': '#221a00', # Darker Gold background
            'font_color': '#FFD700',
            'border': 1,
            'top_color': '#FFD700',
            'bottom_color': '#FFD700',
            'left_color': '#FFD700',
            'right_color': '#FFD700'
        }

    @staticmethod
    def rank_silver(workbook):
        return {
            'bg_color': '#0f0f0f', 
            'font_color': '#CCCCCC',
            'border': 1,
            'border_color': '#444444'
        }

