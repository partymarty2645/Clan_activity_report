
import pandas as pd
import logging
import os
import xlsxwriter
import shutil
from datetime import datetime, timedelta, timezone
from core.config import Config
from core.timestamps import TimestampHelper
from core.utils import get_unique_filename
from core.performance import timed_operation

from reporting.styles import Theme, ExcelFormats

logger = logging.getLogger("ExcelReporter")

class ExcelReporter:
    @timed_operation("Excel Report Generation")
    def generate(self, analytics_service, metadata=None):
        if not analytics_service:
            from database.connector import SessionLocal
            from core.analytics import AnalyticsService
            db = SessionLocal()
            try:
                analytics_service = AnalyticsService(db)
            finally:
                db.close()

        # 1. Fetch Data
        cutoff_7d = TimestampHelper.cutoff_days_ago(7)
        cutoff_30d = TimestampHelper.cutoff_days_ago(30)
        cutoff_90d = TimestampHelper.cutoff_days_ago(90)
        cutoff_365d = TimestampHelper.cutoff_days_ago(365)
        cutoff_lifetime = datetime(2020, 1, 1, tzinfo=timezone.utc)

        latest_snaps_raw = analytics_service.get_latest_snapshots()
        # Convert {ID: Snap} to {Username: Snap} using UsernameNormalizer
        # This aligns with the rest of the report which expects username keys
        from core.usernames import UsernameNormalizer
        latest_snaps = {}
        for snap in latest_snaps_raw.values():
            if snap.username:
                latest_snaps[UsernameNormalizer.normalize(snap.username)] = snap

        min_timestamps = analytics_service.get_min_timestamps() # Fallback for lifetime gains
        
        past_7d = analytics_service.get_snapshots_at_cutoff(cutoff_7d)
        past_30d = analytics_service.get_snapshots_at_cutoff(cutoff_30d)
        past_90d = analytics_service.get_snapshots_at_cutoff(cutoff_90d)
        past_365d = analytics_service.get_snapshots_at_cutoff(cutoff_365d)

        msgs_7d = analytics_service.get_message_counts(cutoff_7d)
        msgs_30d = analytics_service.get_message_counts(cutoff_30d)
        msgs_90d = analytics_service.get_message_counts(cutoff_90d)
        msgs_total = analytics_service.get_message_counts(cutoff_lifetime)

        gains_7d = analytics_service.calculate_gains(latest_snaps, past_7d, staleness_limit_days=14)
        gains_30d = analytics_service.calculate_gains(latest_snaps, past_30d, staleness_limit_days=60)
        gains_90d = analytics_service.calculate_gains(latest_snaps, past_90d, staleness_limit_days=180)
        
        # YEAR GAINS: Pass fallback_map=min_timestamps
        # This ensures users who joined <1 year ago use their first snapshot as the baseline
        gains_365d = analytics_service.calculate_gains(
            latest_snaps, 
            past_365d, 
            staleness_limit_days=None,
            fallback_map=min_timestamps
        )
        
        # FILTER: Only include users who are present in the Metadata (i.e. Active Clan Members)
        # This removes "Ghost" users who have left but still have snapshots.
        if metadata:
            active_users = set(metadata.keys())
            # Normalize latest_snaps keys just in case, though they should be normalized 
            latest_snaps = {k: v for k, v in latest_snaps.items() if k in active_users}
            
        logger.info(f"Generating report for {len(latest_snaps)} active members.")

        # 2. Build Rows
        rows = []
        for user, snap in latest_snaps.items():
            rank_str = "Member"
            joined_str = "N/A"
            
            if metadata:
                # Metadata lookup needs to be robust. 
                # Metadata keys should be normalized in report_sqlite.py, but let's be safe.
                # analytics keys are normalized.
                m = metadata.get(user) 
                
                if m:
                    rank_str = getattr(m, 'role', None) or m.get('role', 'Member')
                    raw_joined = getattr(m, 'joined_at', None) or m.get('joined_at', None)
                    
                    if raw_joined:
                        try:
                            # Handle datetime objects directly
                            if isinstance(raw_joined, datetime):
                                joined_str = raw_joined.strftime("%d/%m/%Y")
                            # Handle string ISO formats 'YYYY-MM-DD...'
                            elif isinstance(raw_joined, str):
                                # Clean potential usage of T or space
                                date_part = raw_joined.split('T')[0].split(' ')[0]
                                y, m_part, d = date_part.split('-')
                                joined_str = f"{d}/{m_part}/{y}"
                        except Exception as e:
                             pass
                
                # Fallback: If joined_str still N/A, try min_timestamps (First Seen)
                if joined_str == "N/A" and min_timestamps and user in min_timestamps:
                    try:
                         first_seen = min_timestamps[user].timestamp
                         if first_seen:
                             joined_str = first_seen.strftime("%d/%m/%Y")
                    except:
                        pass

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
                'XP 365d': gains_365d.get(user, {}).get('xp', 0),
                
                # Boss
                'Boss 7d': gains_7d.get(user, {}).get('boss', 0),
                'Boss 30d': gains_30d.get(user, {}).get('boss', 0),
                'Boss 90d': gains_90d.get(user, {}).get('boss', 0),
                'Boss 365d': gains_365d.get(user, {}).get('boss', 0),
                
                # Totals (Lifetime)
                'Total Msgs': msgs_total.get(user, 0),
                'Total XP': snap.total_xp or 0, 
                'Total Boss': snap.total_boss_kills or 0
            }
            rows.append(row)

        # 3. Sort & Decorate (Medals)
        df = pd.DataFrame(rows)
        if not df.empty:
            # Sort by Total Messages, then Total XP
            df.sort_values(by=['Total Msgs', 'Total XP'], ascending=[False, False], inplace=True)
            df.insert(0, '#', range(1, len(df) + 1))

            # Apply Icons to Top 3
            # We iterate differently or apply during write to not break strings?
            # Ideally applied during write, or pre-process Name string here.
            # Let's pre-process Name column since it's cleaner.
            
            def add_medal(row):
                rank = row['#']
                name = row['Name']
                if rank == 1: return f"👑 {name}"
                if rank == 2: return f"🥈 {name}"
                if rank == 3: return f"🥉 {name}"
                return name
            
            df['Name'] = df.apply(add_medal, axis=1)

        # 4. Generate Output (Merged Logic: One File to Rule Them All)
        final_file = Config.OUTPUT_FILE_XLSX
        temp_file = final_file + ".temp.xlsx"
        
        try:
            with pd.ExcelWriter(temp_file, engine='xlsxwriter') as writer:
                self._write_roster_sheet(writer, df)
            
            self._atomic_save(temp_file, final_file)
            
        except Exception as e:
            logger.error(f"Failed to generate Report: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _write_roster_sheet(self, writer, df):
        sheet_name = 'Clan Roster'
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet
        
        (max_row, max_col) = df.shape

        # -- FORMATS --
        base_fmt = ExcelFormats.base(workbook)

        # Dynamic Headers per Group
        fmt_head_id = workbook.add_format(ExcelFormats.get_header_format(workbook, Theme.TEXT_ID, Theme.BORDER_ID))
        fmt_head_msg = workbook.add_format(ExcelFormats.get_header_format(workbook, Theme.TEXT_MSG, Theme.BORDER_MSG))
        fmt_head_xp = workbook.add_format(ExcelFormats.get_header_format(workbook, Theme.TEXT_XP, Theme.BORDER_XP))
        fmt_head_boss = workbook.add_format(ExcelFormats.get_header_format(workbook, Theme.TEXT_BOSS, Theme.BORDER_BOSS))

        # Helper: Stripe Generator
        def create_stripe_formats(bg_odd, bg_even, text_color):
            f_odd = workbook.add_format(base_fmt)
            f_odd.set_bg_color(bg_odd)
            f_odd.set_font_color(text_color)
            f_odd.set_num_format('#,##0')
            
            f_even = workbook.add_format(base_fmt)
            f_even.set_bg_color(bg_even)
            f_even.set_font_color(text_color)
            f_even.set_num_format('#,##0')
            return f_odd, f_even

        # Generate Group Formats
        fmt_id_odd, fmt_id_even = create_stripe_formats(Theme.BG_ID_ODD, Theme.BG_ID_EVEN, Theme.TEXT_ID)
        fmt_msg_odd, fmt_msg_even = create_stripe_formats(Theme.BG_MSG_ODD, Theme.BG_MSG_EVEN, Theme.TEXT_MSG)
        fmt_xp_odd, fmt_xp_even = create_stripe_formats(Theme.BG_XP_ODD, Theme.BG_XP_EVEN, Theme.TEXT_XP)
        fmt_boss_odd, fmt_boss_even = create_stripe_formats(Theme.BG_BOSS_ODD, Theme.BG_BOSS_EVEN, Theme.TEXT_BOSS)

        # Zero Alarm
        fmt_zero = workbook.add_format(base_fmt)
        fmt_zero.set_bg_color(Theme.BG_ZERO) 
        fmt_zero.set_font_color(Theme.TEXT_ZERO)
        fmt_zero.set_bold(True)
        fmt_zero.set_align('center')

        # -- WRITE HEADERS --
        cols = df.columns
        for i, col in enumerate(cols):
            # Select Header Style
            if 'Msg' in col or 'Total' in col and 'Msgs' in col:
                h_fmt = fmt_head_msg
            elif 'XP' in col:
                h_fmt = fmt_head_xp
            elif 'Boss' in col:
                h_fmt = fmt_head_boss
            else:
                h_fmt = fmt_head_id
            
            worksheet.write(0, i, col, h_fmt)
            
            # Widths
            if col == 'Name': worksheet.set_column(i, i, 25)
            elif col == '#': worksheet.set_column(i, i, 5)
            elif 'Total' in col: worksheet.set_column(i, i, 16)
            else: worksheet.set_column(i, i, 14)

        # -- WRITE DATA ROWS --
        for r_idx, row_data in df.iterrows():
            current_row = r_idx + 1 # 1-indexed (Head is 0)
            is_even = (r_idx % 2 == 0)
            
            for c_idx, value in enumerate(row_data):
                col_name = cols[c_idx]

                # Zero Check
                if isinstance(value, (int, float)) and value == 0:
                    worksheet.write(current_row, c_idx, value, fmt_zero)
                    continue
                
                # Determine Style Group
                if 'Msg' in col_name or ('Total' in col_name and 'Msgs' in col_name):
                    fmt = fmt_msg_even if is_even else fmt_msg_odd
                elif 'XP' in col_name:
                    fmt = fmt_xp_even if is_even else fmt_xp_odd
                elif 'Boss' in col_name:
                    fmt = fmt_boss_even if is_even else fmt_boss_odd
                else:
                    fmt = fmt_id_even if is_even else fmt_id_odd
                
                # Align Text left, Numbers center (Modify format on fly? No, create separate text/num sets)
                # Optimization: Text is mostly left, Num center. 
                # Let's strict force alignment based on type.
                # Actually, simpler: Identity = Left, Stats = Center
                
                if c_idx > 2: # Stats Columns
                    # Format is already center-ish from base, but numbers work best right or center.
                    # Let's trust the base alignment set in create_stripe_formats
                    pass
                else: 
                    # Name/Group/Joined -> Force Left?
                    # We can clone and modify or just accept center for now to save perf.
                    pass

                worksheet.write(current_row, c_idx, value, fmt)
            
            worksheet.set_row(current_row, 24) # Row Height

        worksheet.freeze_panes(1, 2)
        worksheet.autofilter(0, 0, max_row, max_col - 1)
        worksheet.hide_gridlines(2)

    def _atomic_save(self, temp, final):
        if os.path.exists(final):
            try:
                os.remove(final)
            except PermissionError:
                final = get_unique_filename(final.replace(".xlsx", "_backup.xlsx"))
        try:
             os.replace(temp, final)
             logger.info(f"Report Saved: {final}")
        except Exception as e:
             logger.error(f"Save Failed: {e}")

reporter = ExcelReporter()
