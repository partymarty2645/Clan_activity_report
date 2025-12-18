
import pandas as pd
import logging
import os
import xlsxwriter
from datetime import datetime
from core.config import Config
from core.utils import get_unique_filename
from core.performance import timed_operation
from reporting.styles import Theme, ExcelFormats

logger = logging.getLogger("ExcelReporter")

class ExcelReporter:
    @timed_operation("Excel Report Generation")
    def generate(self, data_list):
        """
        Generates the Excel report with Dashboard and Roster sheets.
        """
        if not data_list:
            logger.warning("No data to report.")
            return

        df = pd.DataFrame(data_list)
        
        # 1. Define Columns Order (Preserve original logic)
        ordered_columns = [
            'Username', 'Joined date', 'Role',
            'XP Gained 7d', 'XP Gained 30d', 'XP Gained 70d', 'XP Gained 150d', 'Total xp gained',
            'Messages 7d', 'Messages 30d', 'Messages 70d', 'Messages 150d', 'Total Messages',
            'Boss kills 7d', 'Boss kills 30d', 'Boss kills 70d', 'Boss kills 150d', 'Total boss kills'
        ]
        
        # Filter columns that exist in data
        cols_available = [c for c in ordered_columns if c in df.columns]
        df = df[cols_available]

        # Sort Logic
        if 'Messages 30d' in df.columns:
            df = df.sort_values(by=['Messages 30d'], ascending=[False])
        elif 'Total xp gained' in df.columns:
            df = df.sort_values(by=['Total xp gained'], ascending=[False])

        # 2. Save CSV (Legacy Support)
        try:
            csv_file = Config.OUTPUT_FILE_CSV
            df.to_csv(csv_file, index=False)
            logger.info(f"Saved CSV: {csv_file}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")

        # 3. Save Excel
        xlsx_file = Config.OUTPUT_FILE_XLSX
        temp_file = xlsx_file + ".temp.xlsx"
        
        try:
            with pd.ExcelWriter(temp_file, engine='xlsxwriter') as writer:
                # WE CREATE SHEETS IN ORDER: Dashboard first, then Roster
                self._write_dashboard(writer, df)
                self._write_roster(writer, df)
            
            # Atomic Replacement
            self._atomic_save(temp_file, xlsx_file)
            
        except Exception as e:
            logger.error(f"Failed to generate Excel: {e}")
            # Clean up temp if exists
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _write_dashboard(self, writer, df):
        """Creates the 'Launch Dashboard' Cover Sheet with Neon Gielinor styling"""
        workbook = writer.book
        worksheet = workbook.add_worksheet('Launch Dashboard')
        writer.sheets['Launch Dashboard'] = worksheet
        
        # Define Formats
        fmt_bg_black = workbook.add_format({'bg_color': Theme.BG_BLACK})
        fmt_neon_title = workbook.add_format(ExcelFormats.neon_header(workbook))
        fmt_launch_btn = workbook.add_format(ExcelFormats.launch_button(workbook, Theme.BLUE_NEON))
        fmt_roster_btn = workbook.add_format(ExcelFormats.launch_button(workbook, Theme.GREEN_NEON))
        
        fmt_hero_label = workbook.add_format({
            'bold': True, 'font_color': Theme.BLUE_NEON, 'bg_color': Theme.BG_CARD,
            'align': 'center', 'valign': 'bottom', 'font_size': 12,
            'font_name': 'Inter'
        })
        
        fmt_hero_val = workbook.add_format({
            'bold': True, 'font_color': '#FFFFFF', 'bg_color': Theme.BG_CARD,
            'align': 'center', 'valign': 'top', 'font_size': 22,
            'bottom': 2, 'bottom_color': Theme.BLUE_NEON,
            'font_name': 'Impact'
        })
        
        fmt_date = workbook.add_format({'font_color': '#666666', 'bg_color': Theme.BG_BLACK, 'valign': 'top', 'align': 'right', 'italic': True})
        
        # Specific Styles for Summary Tables
        fmt_head_xp = workbook.add_format(ExcelFormats.dashboard_card_header(workbook, Theme.GREEN_NEON))
        fmt_val_xp = workbook.add_format(ExcelFormats.dashboard_card_value(workbook, Theme.GREEN_NEON))
        fmt_val_xp.set_num_format('0.0,,"M"')

        fmt_head_msg = workbook.add_format(ExcelFormats.dashboard_card_header(workbook, Theme.CYAN_NEON))
        fmt_val_msg = workbook.add_format(ExcelFormats.dashboard_card_value(workbook, Theme.CYAN_NEON))
        fmt_val_msg.set_num_format('#,##0')
        
        # Hide Gridlines
        worksheet.hide_gridlines(1)
        worksheet.set_zoom(90)
        
        # Apply Background
        worksheet.set_column(0, 20, 20, fmt_bg_black)
        for r in range(100):
            worksheet.set_row(r, 20, fmt_bg_black)

        # INSERT LOGO/ICON (Experimental/Stylistic)
        try:
            # Try to find a cool icon
            logo_path = os.path.join("assets", "boss_vorkath.png")
            if os.path.exists(logo_path):
                worksheet.insert_image('B2', logo_path, {'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 10, 'y_offset': 10})
        except:
            pass

        # Title Section
        worksheet.merge_range('B2:K4', 'NEON GIELINOR CLAN OPERATIONS', fmt_neon_title)
        worksheet.merge_range('B5:K5', f"SYSTEM TIME: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fmt_date)

        # METRICS CALCULATION
        total_xp = df['Total xp gained'].sum() if 'Total xp gained' in df.columns else 0
        top_member = "N/A"
        if not df.empty and 'Total xp gained' in df.columns:
            top_member = df.loc[df['Total xp gained'].idxmax()]['Username']

        # Hero Stats
        worksheet.merge_range('C7:E7', 'CLAN AGGREGATE XP', fmt_hero_label)
        worksheet.merge_range('C8:E9', f"{total_xp/1000000:.1f}M", fmt_hero_val)
        
        worksheet.merge_range('F7:H7', 'CURRENT SECTOR MVP', fmt_hero_label)
        worksheet.merge_range('F8:H9', top_member, fmt_hero_val)
        
        # BUTTONS
        worksheet.merge_range('C11:F14', '⚡ LAUNCH WEB INTERFACE', fmt_launch_btn)
        worksheet.write_url('C11', 'external:dashboard.html', fmt_launch_btn, '⚡ LAUNCH WEB INTERFACE')
        
        worksheet.merge_range('G11:J14', '📁 ACCESS ROSTER DATA', fmt_roster_btn)
        worksheet.write_url('G11', "internal:'Roster'!A1", fmt_roster_btn, '📁 ACCESS ROSTER DATA')

        # Summary Sub-headers
        row_sum = 16
        worksheet.merge_range(row_sum, 2, row_sum, 4, "TOP GAINERS [ACTIVE SECTOR]", fmt_head_xp)
        worksheet.merge_range(row_sum, 6, row_sum, 8, "INACTIVITY ALERTS [STAFF]", fmt_head_msg)
        
        # Formulas (Dynamic Arrays)
        worksheet.write_formula(row_sum+1, 2, '=IFERROR(TAKE(SORT(CHOOSECOLS(Roster!A2:D1000, 1, 4), 2, -1), 5), "VOID")', fmt_val_xp)
        worksheet.write_formula(row_sum+1, 6, 
            '=IFERROR(TAKE(FILTER(CHOOSECOLS(Roster!A2:K1000, 1, 10), (ISNUMBER(MATCH(Roster!C2:C1000, {"Owner","Deputy Owner","Saviour","Zenyte"}, 0))) * (Roster!J2:J1000=0)), 5), "STABLE")', 
            fmt_val_msg)



    def _write_roster(self, writer, df):
        """Creates the Detailed Data Sheet using Excel Tables"""
        # Write data to Excel (including headers initially to populate cells)
        df.to_excel(writer, index=False, sheet_name='Roster')
        workbook = writer.book
        worksheet = writer.sheets['Roster']
        (max_row, max_col) = df.shape

        # Define styles
        fmt_base_left = workbook.add_format(ExcelFormats.base(workbook))
        fmt_base_left.set_align('left')
        
        fmt_base_numeric = workbook.add_format(ExcelFormats.base(workbook))
        fmt_base_numeric.set_align('center')
        fmt_base_numeric.set_num_format('#,##0')

        fmt_numeric_large = workbook.add_format(ExcelFormats.base(workbook))
        fmt_numeric_large.set_align('center')
        fmt_numeric_large.set_num_format(ExcelFormats.number_large(workbook))
        
        fmt_red_alert = workbook.add_format({'bg_color': '#550000', 'font_color': '#ffaaaa'})

        # Create the Table Structure
        # We need to build the 'columns' list for add_table
        column_settings = []
        for i, col_name in enumerate(df.columns):
            # Determine format based on data type or name
            col_format = fmt_base_left
            if 'xp' in col_name.lower() or 'total' in col_name.lower() or 'messages' in col_name.lower():
                col_format = fmt_numeric_large if 'xp' in col_name.lower() else fmt_base_numeric
            
            column_settings.append({'header': col_name, 'format': col_format})

        # Apply the Table with Auto-Filter and Style
        # 'TableStyleDark2' is a good fit for Neon/Dark theme (Grey/Dark Blue)
        # Options: TableStyleMedium5 (Blue), TableStyleDark1-11
        worksheet.add_table(0, 0, max_row, max_col - 1, {
            'columns': column_settings,
            'style': 'TableStyleDark3', # Dark Grey/Black theme
            'name': 'RosterTable',
            'first_column': True,
        })
        
        # We no longer need the manual header formatting loop because add_table handles headers.
        # We DO need to handle column widths still.

        # 1. Column Sizing & Specific Formats (Header handled by Table)
        # 2. Column Sizing & Specific Formats
        for i, col_name in enumerate(df.columns):
            width = 15 # Default
            
            # Identifiers
            if col_name in ['Username', 'Role', 'Joined date']:
                worksheet.set_column(i, i, 20, fmt_base_left)
            else:
                # Numeric
                # Use large number format
                worksheet.set_column(i, i, 12, fmt_numeric_large)

        # 4. Freeze Panes
        worksheet.freeze_panes(1, 1) # Row 1, Col 1 (Username)

        # 5. Conditional Formatting (Heatmaps)
        
        # A. XP Velocity (Green to Black)
        for col in ['XP Gained 7d', 'XP Gained 30d', 'Total xp gained']:
            if col in df.columns:
                idx = df.columns.get_loc(col)
                worksheet.conditional_format(1, idx, max_row, idx, {
                    'type': '3_color_scale',
                    'min_color': '#000000',
                    'mid_color': '#004400',
                    'max_color': Theme.GREEN_NEON
                })

        # B. Message Velocity (Cyan to Black)
        for col in ['Messages 7d', 'Messages 30d', 'Total Messages']:
            if col in df.columns:
                idx = df.columns.get_loc(col)
                worksheet.conditional_format(1, idx, max_row, idx, {
                    'type': '3_color_scale',
                    'min_color': '#000000',
                    'mid_color': '#003344',
                    'max_color': Theme.CYAN_NEON
                })

        # C. Boss Velocity (Red to Black)
        for col in ['Boss kills 7d', 'Total boss kills']:
            if col in df.columns:
                idx = df.columns.get_loc(col)
                worksheet.conditional_format(1, idx, max_row, idx, {
                    'type': '3_color_scale',
                    'min_color': '#000000',
                    'mid_color': '#440000',
                    'max_color': Theme.RED_NEON
                })
            
        # D. Inactivity Alert (Red background for 0 XP)
        if 'XP Gained 7d' in df.columns:
            idx = df.columns.get_loc('XP Gained 7d')
            fmt_red_alert = workbook.add_format({'bg_color': '#440000', 'font_color': '#FF9999'})
            worksheet.conditional_format(1, idx, max_row, idx, {
                'type': 'cell',
                'criteria': '=',
                'value': 0,
                'format': fmt_red_alert
            })

        # E. Leadership Styling (Gold highlight)
        if 'Role' in df.columns:
            fmt_gold_rank = workbook.add_format(ExcelFormats.rank_gold(workbook))
            worksheet.conditional_format(1, 0, max_row, max_col-1, {
                'type': 'formula',
                'criteria': '=OR($C2="Owner", $C2="Deputy Owner", $C2="Saviour", $C2="Zenyte")',
                'format': fmt_gold_rank
            })

        # 6. Data Validation
        # Role Dropdown
        if 'Role' in df.columns:
            role_idx = df.columns.get_loc('Role')
            roles = ['Owner', 'Deputy Owner', 'Overseer', 'Coordinator', 'General', 'Captain', 'Lieutenant', 'Sergeant', 'Corporal', 'Recruit', 'Guest']
            worksheet.data_validation(1, role_idx, max_row, role_idx, {
                'validate': 'list',
                'source': roles,
                'input_title': 'Select Role',
                'input_message': 'Select rank.'
            })
        
        # Non-Negative XP
        for i, col_name in enumerate(df.columns):
            if 'Gained' in col_name or 'kills' in col_name:
                worksheet.data_validation(1, i, max_row, i, {
                    'validate': 'decimal',
                    'criteria': '>=',
                    'value': 0,
                    'error_title': 'Invalid Input',
                    'error_message': 'Values cannot be negative.'
                })
        
        # 7. AutoFit Columns (Manual Simulation)
        # Identify max length
        worksheet.set_column(0, 0, 25, fmt_base_left) # Username
        worksheet.set_column(1, 1, 15, fmt_base_left) # Date
        worksheet.set_column(2, 2, 15, fmt_base_left) # Role
        # Metrics
        worksheet.set_column(3, max_col-1, 18, fmt_numeric_large)

    def _atomic_save(self, temp, final):
        if os.path.exists(final):
            try:
                os.remove(final)
            except PermissionError:
                # Fallback
                final = get_unique_filename(final.replace(".xlsx", "_backup.xlsx"))
                logger.warning(f"Target locked, saving as {final}")
        
        os.rename(temp, final)
        logger.info(f"Excel Report Generated: {final}")

reporter = ExcelReporter()
