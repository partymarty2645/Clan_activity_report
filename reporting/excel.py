import pandas as pd
import logging
import os
from datetime import datetime
from core.config import Config
from core.utils import get_unique_filename

logger = logging.getLogger("ExcelReporter")

class ExcelReporter:
    def generate(self, data_list):
        """
        Generates the Excel report from a list of dictionaries.
        data_list: List of dicts with keys matching the columns.
        """
        if not data_list:
            logger.warning("No data to report.")
            return

        df = pd.DataFrame(data_list)
        
        # 1. Define Columns Order
        # Just use what's provided or defined in Config?
        # Ideally we stick to the user's explicit order requirements
        ordered_columns = [
            'Username', 'Joined date', 'Role',
            'XP Gained 7d', 'XP Gained 30d', 'XP Gained 70d', 'XP Gained 150d', 'Total xp gained',
            'Messages 7d', 'Messages 30d', 'Messages 70d', 'Messages 150d', 'Total Messages',
            'Boss kills 7d', 'Boss kills 30d', 'Boss kills 70d', 'Boss kills 150d', 'Total boss kills'
        ]
        
        # Filter/Sort
        cols_available = [c for c in ordered_columns if c in df.columns]
        df = df[cols_available]
        
        if 'Messages 30d' in df.columns:
            df = df.sort_values(by=['Messages 30d'], ascending=[False])
        elif 'Total xp gained' in df.columns:
            df = df.sort_values(by=['Total xp gained'], ascending=[False])

        # 2. Save CSV
        try:
            csv_file = Config.OUTPUT_FILE_CSV
            df.to_csv(csv_file, index=False)
            logger.info(f"Saved CSV: {csv_file}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")

        # 3. Save Excel (Atomic with Fallback)
        xlsx_file = Config.OUTPUT_FILE_XLSX 
        temp_file = xlsx_file + ".temp.xlsx"
        
        try:
            # Write to temp first
            with pd.ExcelWriter(temp_file, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Summary')
                self._apply_styles(writer, df)
            
            # Atomic Replacement
            try:
                if os.path.exists(xlsx_file):
                    os.remove(xlsx_file)
                os.rename(temp_file, xlsx_file)
                logger.info(f"Saved Excel: {xlsx_file}")
            except PermissionError:
                # Fallback: File is open by user
                backup_name = get_unique_filename(xlsx_file.replace(".xlsx", "_backup.xlsx"))
                os.rename(temp_file, backup_name)
                logger.warning(f"Target file locked! Saved as backup: {backup_name}")
            except Exception as e:
                logger.error(f"Error swapping files: {e}")
                
        except Exception as e:
            logger.error(f"Failed to generate Excel: {e}")

    def _apply_styles(self, writer, df):
        workbook = writer.book
        worksheet = writer.sheets['Summary']
        (max_row, max_col) = df.shape
        
        # 1. Premium View Settings
        worksheet.hide_gridlines(2) # Hide all gridlines
        worksheet.set_zoom(100)
        
        # 2. Base Formats (User Style matches Screenshot)
        bg = Config.EXCEL_BG_COLOR 
        fg = Config.EXCEL_FONT_COLOR
        border_color = '#FFFFFF' # White borders seen in screenshot? Or light grey. Let's use light grey.
        border_color = '#d0d7e5' 
        
        font_size = 14
        
        # Base Data Format
        fmt_base = workbook.add_format({
            # 'font_name': 'Calibri', # Default
            'valign': 'vcenter',
            'border': 1, 
            'border_color': border_color,
            'num_format': '#,##0',
            'bg_color': bg, 
            'font_color': fg,
            'font_size': font_size
        })
        
        # Header Format (Row 1) 
        # Screenshot shows black/dark header with white text, filters on.
        fmt_header = workbook.add_format({
            'bold': True, 
            'border': 1,
            'border_color': border_color,
            'bg_color': '#000000', # Black header
            'font_color': '#FFFFFF',
            'valign': 'vcenter',
            'font_size': font_size
        })
        
        # Apply Base & Header manually
        # worksheet.set_column(0, max_col - 1, 15, fmt_base) # REMOVED: Caused infinite borders
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, fmt_header)
        
        # 3. Column Groups (User Colors)
        # Using the exact hex codes from Config
        formats = {
            'identity': workbook.add_format({'border': 1, 'border_color': border_color, 'bg_color': Config.COLOR_IDENTITY, 'font_color': '#FFFFFF', 'num_format': '#,##0', 'font_size': font_size}),
            'xp': workbook.add_format({'border': 1, 'border_color': border_color, 'bg_color': Config.COLOR_XP, 'font_color': '#FFFFFF', 'num_format': '#,##0', 'font_size': font_size}),
            'messages': workbook.add_format({'border': 1, 'border_color': border_color, 'bg_color': Config.COLOR_MESSAGES, 'font_color': '#FFFFFF', 'num_format': '#,##0', 'font_size': font_size}),
            'boss': workbook.add_format({'border': 1, 'border_color': border_color, 'bg_color': Config.COLOR_BOSS, 'font_color': '#FFFFFF', 'num_format': '#,##0', 'font_size': font_size}),
        }
        

        
        # Apply Column Formats
        for i, col_name in enumerate(df.columns):
            c = col_name.lower()
            
            # Logic for 6 Groups
            if c in ['username', 'role', 'rank', 'score', 'joined date']:
                f = formats['identity']
            elif 'xp' in c or 'gained' in c: 
                f = formats['xp']
            elif 'boss' in c: 
                f = formats['boss']
            elif 'messages' in c:
                f = formats['messages']
            else:
                f = fmt_base 
            
            # Auto-Fit Width Calculation
            max_data_len = 0
            if not df.empty:
                 # Check lengths of string representation of data in this column
                 series_len = df[col_name].astype(str).map(len)
                 if not series_len.empty:
                    max_data_len = series_len.max()
            
            header_len = len(str(col_name))
            
            # scaling for Font Size 14 (approx 1.4x default 11pt) + Bold Header padding
            # max_data_len is raw char count. 
            count = max(max_data_len, header_len)
            
            # Apply scaling factor
            est_width = (count * 1.5) + 2 
            
            # Clamp width
            width = min(max(est_width, 12), 80)
            worksheet.set_column(i, i, width) # Set WIDTH ONLY (No Format)
            
            # Apply Format to Data Cells Explicitly
            vals = df[col_name].values
            for r_idx, val in enumerate(vals):
                if pd.isna(val): val = ""
                worksheet.write(r_idx + 1, i, val, f)
            
        worksheet.freeze_panes(1, 1)
        worksheet.autofilter(0, 0, max_row, max_col - 1)
        
        # Conditional Format (Zero) - Dark Grey BG + Red Text
        if Config.EXCEL_ZERO_HIGHLIGHT:
            red_fmt = workbook.add_format({
                'font_color': Config.EXCEL_ZERO_FONT_COLOR, 
                'bg_color': Config.EXCEL_ZERO_BG_COLOR,
                'border': 1,
                'border_color': border_color
            })
            worksheet.conditional_format(1, 0, max_row, max_col - 1, {
                'type': 'cell', 'criteria': '==', 'value': 0, 'format': red_fmt
            })
            


reporter = ExcelReporter()
