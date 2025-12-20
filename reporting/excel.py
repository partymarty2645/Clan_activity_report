
import pandas as pd
import logging
import os
import xlsxwriter
from datetime import datetime, timedelta, timezone
from core.config import Config
from core.utils import get_unique_filename
from core.performance import timed_operation

# Define Theme Colors Locally for "Executive Night Mode"
class DarkTheme:
    BG_DARK = '#121212'
    TEXT_LIGHT = '#E0E0E0'
    HEADER_BG = '#1E1E1E'
    
    # Category Colors
    XP_GREEN = '#006400'     # Dark Green for text/headers
    XP_SCALE_MAX = '#33FF33' # Bright Green for high values
    
    BOSS_RED = '#8B0000'     # Dark Red for headers
    BOSS_SCALE_MAX = '#FF4500' # Orange-Red for high values
    
    MSG_BLUE = '#00008B'     # Dark Blue for headers
    MSG_SCALE_MAX = '#00BFFF' # Deep Sky Blue for high values
    
    ZERO_RED = '#FF0000'     # Pure Red for zeros

    LINK_COLOR = '#44AAFF'

logger = logging.getLogger("ExcelReporter")

class ExcelReporter:
    @timed_operation("Excel Report Generation")
    def generate(self, analytics_service, metadata=None):
        """
        Generates:
        1. clan_report_data.xlsx (Raw Data)
        2. clan_report_full.xlsx (Formatted Executive Report)
        """
        if not analytics_service:
            from database.connector import SessionLocal
            from core.analytics import AnalyticsService
            db = SessionLocal()
            try:
                analytics_service = AnalyticsService(db)
            finally:
                db.close()

        # 1. Define Dates
        now_utc = datetime.now(timezone.utc)
        cutoff_7d = now_utc - timedelta(days=7)
        cutoff_30d = now_utc - timedelta(days=30)
        cutoff_90d = now_utc - timedelta(days=90)
        cutoff_365d = now_utc - timedelta(days=365)
        cutoff_lifetime = datetime(2020, 1, 1, tzinfo=timezone.utc)

        # 2. Fetch Data (Bulk)
        latest_snaps = analytics_service.get_latest_snapshots()
        past_7d = analytics_service.get_snapshots_at_cutoff(cutoff_7d)
        past_30d = analytics_service.get_snapshots_at_cutoff(cutoff_30d)
        past_90d = analytics_service.get_snapshots_at_cutoff(cutoff_90d)
        past_365d = analytics_service.get_snapshots_at_cutoff(cutoff_365d)

        msgs_7d = analytics_service.get_message_counts(cutoff_7d)
        msgs_30d = analytics_service.get_message_counts(cutoff_30d)
        msgs_90d = analytics_service.get_message_counts(cutoff_90d)
        msgs_total = analytics_service.get_message_counts(cutoff_lifetime)

        # 3. Calculate Deltas
        gains_7d = analytics_service.calculate_gains(latest_snaps, past_7d)
        gains_30d = analytics_service.calculate_gains(latest_snaps, past_30d)
        gains_90d = analytics_service.calculate_gains(latest_snaps, past_90d)
        gains_365d = analytics_service.calculate_gains(latest_snaps, past_365d)

        # 4. Build Rows
        rows = []
        for user, snap in latest_snaps.items():
            rank_str = "Member"
            joined_str = "N/A"
            
            if metadata:
                m = metadata.get(user.lower())
                if m:
                    rank_str = getattr(m, 'role', None) or m.get('role', 'Member')
                    joined_str = getattr(m, 'joined_at', None) or m.get('joined_at', 'N/A')
                    if isinstance(joined_str, datetime):
                        joined_str = joined_str.strftime("%d-%m-%Y")
                    elif isinstance(joined_str, str) and 'T' in joined_str:
                        try:
                            # Try to parse ISO format if possible, otherwise fallback
                             dt_obj = datetime.fromisoformat(joined_str.replace('Z', '+00:00'))
                             joined_str = dt_obj.strftime("%d-%m-%Y")
                        except Exception:
                             # Fallback to simple string manipulation if parsing fails, but try to rearrange
                             parts = joined_str.split('T')[0].split('-')
                             if len(parts) == 3:
                                 joined_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
                             else:
                                 joined_str = joined_str.split('T')[0]

            row = {
                'Name': user,
                'Joined': joined_str,
                'Rank': rank_str,
                
                # Messages
                'Msgs 7d': msgs_7d.get(user, 0),
                'Msgs 30d': msgs_30d.get(user, 0),
                'Msgs 90d': msgs_90d.get(user, 0),
                
                # XP
                'XP 7d': gains_7d.get(user, {}).get('xp', 0),
                'XP 30d': gains_30d.get(user, {}).get('xp', 0),
                'XP 90d': gains_90d.get(user, {}).get('xp', 0),
                
                # Boss
                'Boss 7d': gains_7d.get(user, {}).get('boss', 0),
                'Boss 30d': gains_30d.get(user, {}).get('boss', 0),
                'Boss 90d': gains_90d.get(user, {}).get('boss', 0),
                
                # Totals
                'Total Msgs': msgs_total.get(user, 0),
                'XP Year': gains_365d.get(user, {}).get('xp', 0), 
                'Boss Year': gains_365d.get(user, {}).get('boss', 0)
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        # 5. Output 1: RAW DATA (clan_report_data.xlsx) - Now Styled (No Link)
        raw_file = "clan_report_data.xlsx"
        raw_temp = raw_file + ".temp.xlsx"
        try:
            with pd.ExcelWriter(raw_temp, engine='xlsxwriter') as writer:
                self._write_styled_sheet(writer, df, include_link=False)
            
            self._atomic_save(raw_temp, raw_file)
        except Exception as e:
            logger.error(f"Failed to generate raw report: {e}")
            if os.path.exists(raw_temp):
                os.remove(raw_temp)

        # 6. Output 2: FULL REPORT (clan_report_full.xlsx) (With Link)
        full_file = "clan_report_full.xlsx"
        temp_file = full_file + ".temp.xlsx"
        
        try:
            with pd.ExcelWriter(temp_file, engine='xlsxwriter') as writer:
                self._write_styled_sheet(writer, df, include_link=True)
            
            self._atomic_save(temp_file, full_file)
            
        except Exception as e:
            logger.error(f"Failed to generate Full Report: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _write_styled_sheet(self, writer, df, include_link=True):
        sheet_name = 'Clan Roster'
        # df.to_excel removed from here, deferred to end of function for layout control
        workbook = writer.book
        worksheet = writer.sheets.get(sheet_name)
        if not worksheet:
             worksheet = workbook.add_worksheet(sheet_name)
             writer.sheets[sheet_name] = worksheet
        
        (max_row, max_col) = df.shape

        # --- FORMATS ---
        
        # Base Format (Dark Inteface)
        base_fmt = {
            'bg_color': DarkTheme.BG_DARK,
            'font_color': DarkTheme.TEXT_LIGHT,
            'font_size': 15,    # User requested Font Size 15
            'font_name': 'Calibri',
            'border': 1,
            'border_color': '#333333'
        }
        
        fmt_string = workbook.add_format(base_fmt)
        fmt_string.set_align('left')
        fmt_string.set_align('vcenter')

        fmt_num = workbook.add_format(base_fmt)
        fmt_num.set_num_format('#,##0')
        fmt_num.set_align('center')
        fmt_num.set_align('vcenter')

        # Header Formats (Category Specific)
        def get_header_fmt(bg_color):
            return workbook.add_format({
                'bold': True,
                'font_color': '#FFFFFF', # White text on colored headers
                'bg_color': bg_color,
                'border': 1,
                'border_color': '#444444',
                'align': 'center',
                'valign': 'vcenter',
                'font_size': 14
            })

        fmt_header_gen = get_header_fmt('#333333') # General (Name, Rank)
        fmt_header_xp = get_header_fmt(DarkTheme.XP_GREEN)
        fmt_header_boss = get_header_fmt(DarkTheme.BOSS_RED)
        fmt_header_msg = get_header_fmt(DarkTheme.MSG_BLUE)

        # Zero Format (Bold Red)
        fmt_zero = workbook.add_format(base_fmt)
        fmt_zero.set_font_color(DarkTheme.ZERO_RED)
        fmt_zero.set_bold(True)
        fmt_zero.set_align('center')
        fmt_zero.set_align('vcenter')
        
        # Link Format
        fmt_link = workbook.add_format({
            'bold': True, 'font_color': DarkTheme.LINK_COLOR, 'bg_color': DarkTheme.BG_DARK,
            'align': 'center', 'valign': 'vcenter', 'underline': True, 'font_size': 16
        })

        # --- LAYOUT & DATA ---
        
        # Determine Rows
        header_row = 1 if include_link else 0
        data_start_row = 2 if include_link else 1
        
        # --- HEADERS ---
        cols = df.columns
        for i, col in enumerate(cols):
            # Determine Header Style
            if 'XP' in col: h_fmt = fmt_header_xp
            elif 'Boss' in col: h_fmt = fmt_header_boss
            elif 'Msgs' in col: h_fmt = fmt_header_msg
            else: h_fmt = fmt_header_gen
            
            worksheet.write(header_row, i, col, h_fmt)
            
            # Column Widths (NO FORMATTING applied to whole column to avoid infinite rows)
            if col == 'Name':
                worksheet.set_column(i, i, 25)
            elif col in ['Joined', 'Rank']:
                worksheet.set_column(i, i, 18)
            else:
                worksheet.set_column(i, i, 15)

        # --- DATA WRITING (Manual Loop for Styling) ---
        # We iterate through the dataframe and write each cell with the base format (borders)
        # This ensures borders/bg only exist where data exists.
        
        for r_idx, row_data in df.iterrows():
            current_row = data_start_row + r_idx
            for c_idx, value in enumerate(row_data):
                # Determine format based on column type
                if isinstance(value, (int, float)):
                    cell_fmt = fmt_num
                else:
                    cell_fmt = fmt_string
                
                # Write cell
                worksheet.write(current_row, c_idx, value, cell_fmt)
                
            # Set Row Height
            worksheet.set_row(current_row, 22)

        # Optional Link
        if include_link:
            worksheet.merge_range('A1:C1', '⚡ VIEW VISUAL DASHBOARD ⚡', fmt_link)
            worksheet.write_url('A1', 'external:clan_dashboard.html', fmt_link, '⚡ VIEW VISUAL DASHBOARD ⚡')
            worksheet.set_row(0, 30)
            
        # Hide Gridlines (for clean look outside table)
        worksheet.hide_gridlines(2)

        # Freeze Panes
        freeze_rows = 2 if include_link else 1
        worksheet.freeze_panes(freeze_rows, 1)
        
        # Auto Filter
        worksheet.autofilter(header_row, 0, max_row + header_row, max_col - 1)
        
        # --- CONDITIONAL FORMATTING ---
        start_row = data_start_row
        
        # 1. VISIBLE ZEROS (Red)
        worksheet.conditional_format(start_row, 3, max_row + start_row - 1, max_col - 1, {
            'type': 'cell',
            'criteria': '=',
            'value': 0,
            'format': fmt_zero
        })

        # 2. Gradient Scales
        for i, col in enumerate(cols):
            if 'XP' in col:
                worksheet.conditional_format(start_row, i, max_row + start_row - 1, i, {
                    'type': '3_color_scale',
                    'min_color': '#222222', 
                    'mid_color': '#114411',
                    'max_color': DarkTheme.XP_SCALE_MAX
                })
            elif 'Boss' in col:
                worksheet.conditional_format(start_row, i, max_row + start_row - 1, i, {
                    'type': '3_color_scale',
                    'min_color': '#222222',
                    'mid_color': '#551111',
                    'max_color': DarkTheme.BOSS_SCALE_MAX
                })
            elif 'Msgs' in col or 'Total Msgs' in col:
                worksheet.conditional_format(start_row, i, max_row + start_row - 1, i, {
                    'type': '3_color_scale',
                    'min_color': '#222222',
                    'mid_color': '#111155',
                    'max_color': DarkTheme.MSG_SCALE_MAX
                })

    def _atomic_save(self, temp, final):
        if os.path.exists(final):
            try:
                os.remove(final)
            except PermissionError:
                final = get_unique_filename(final.replace(".xlsx", "_backup.xlsx"))
                logger.warning(f"Target locked, saving as {final}")
        
        # Use replace to overwrite if final name changed (or if race condition)
        try:
             os.replace(temp, final)
             logger.info(f"Excel Report Generated: {final}")
             
             # Clean up excessive backups if we created one
             if "_backup" in final:
                 base_name = final.split("_backup")[0] + "_backup"
                 # Find all files starting with base_name
                 import glob
                 directory = os.path.dirname(final) or "."
                 # Pattern: clan_report_data_backup*.xlsx
                 pattern = f"{base_name}*.xlsx"
                 full_pattern = os.path.join(directory, pattern)
                 
                 backups = sorted(glob.glob(full_pattern), key=os.path.getmtime)
                 
                 # Keep last 2
                 while len(backups) > 2:
                     oldest = backups.pop(0)
                     try:
                         os.remove(oldest)
                         logger.info(f"Deleted old report backup: {oldest}")
                     except Exception as e:
                         logger.warning(f"Failed to delete old backup {oldest}: {e}")

        except Exception as e:
             logger.error(f"Failed to save file {final}: {e}")

reporter = ExcelReporter()
