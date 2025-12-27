
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
    RED_NEON = Config.COLOR_BOSS if Config.COLOR_BOSS else '#FF3333'

    # =================
    # MULTI-COLOR THEME (NEON GLOW)
    # =================
    
    # 1. Identity (Slate/Gray)
    BG_ID_ODD = '#121212'   # Deepest Gray
    BG_ID_EVEN = '#1a1a1a'  # Slightly lighter
    TEXT_ID = '#E0E0E0'     # Soft White
    BORDER_ID = '#444444'   # Gray Glow

    # 2. Messages (Electric Blue)
    BG_MSG_ODD = '#05051a'  # Deep Navy
    BG_MSG_EVEN = '#0a0a24' # Lighter Navy
    TEXT_MSG = '#00FFFF'    # Electric Cyan
    BORDER_MSG = '#00BFFF'  # Deep Sky Blue Glow

    # 3. XP (Radioactive Green)
    BG_XP_ODD = '#051405'   # Deep Emerald
    BG_XP_EVEN = '#0a1f0a'  # Lighter Emerald
    TEXT_XP = '#00FF00'     # Lime Green
    BORDER_XP = '#00FF00'   # Matrix Green Glow

    # 4. Boss (Toxic Orange)
    BG_BOSS_ODD = '#2a1a0a' # Deep Orange BG
    BG_BOSS_EVEN = '#3e261a' # Lighter Orange
    TEXT_BOSS = '#ffaa00'   # Neon Orange
    BORDER_BOSS = '#ff8800' # Orange Glow

    BG_CARD = '#2D2D30'  # Cards
    BG_HEADER = '#000000' # Pitch Black Headings
    
    # Zeros (Neon Alert)
    # Dark Red Background + Bright White Text + Red Border behavior (if applied)
    BG_ZERO = '#4d0000' # Deep Red Background
    TEXT_ZERO = '#ffcccc' # Whitish Red Text
    
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
            'bg_color': Theme.BG_ID_ODD, # Default
            'border': 1,
            'border_color': Theme.BORDER_GREY,
            'valign': 'vcenter'
        }

    @staticmethod
    def get_header_format(workbook, color, border_color):
        """Dynamic Header Generator"""
        return {
            'bold': True,
            'font_color': color,
            'bg_color': Theme.BG_HEADER,
            'bottom': 2, # Thick glowing bottom
            'bottom_color': border_color,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12,
            'font_name': 'Segoe UI' # Clean Modern
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
