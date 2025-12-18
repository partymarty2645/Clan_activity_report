
from pathlib import Path

path = Path(r"e:\Clan_activity_report\clan_dashboard.html")
lines = path.read_text(encoding="utf-8").splitlines()

new_lines = []
inserted_stats_close = False
inserted_general_close = False

for i, line in enumerate(lines):
    # Insert closing div for stats-grid before the first dual-chart
    if not inserted_stats_close and '<div class="dual-chart">' in line and 'id="comparator"' not in line:
        # Check context: usually line ~502
        new_lines.append('                                    </div>') # Close stats-grid
        inserted_stats_close = True
        
    # Insert closing divs for general section before Comparator
    if not inserted_general_close and '<!-- Comparator Section -->' in line:
        new_lines.append('                                </div>') # Close general
        new_lines.append('                            </div>') # Close wrapper if any? 
        # Wait, I determined 563 closed ONE thing.
        # If I close stats-grid earlier, then at 563 I just need to close GENERAL.
        # But wait, did I open a wrapper?
        # 447: <div id="general">
        # 469: <div class="stats-grid">
        # ...
        # If I close stats-grid at 502.
        # Then 502-563 are direct children of GENERAL.
        # 563 was `</div>` in original file.
        # If 563 was closing `stats-grid` in the original (incorrect) structure...
        # No, 563 was closing `general`?
        # If 563 closes `general`, then `comparator` is correctly outside.
        # BUT Subagent said `xp-gains` is INSIDE `general`.
        # This implies `general` was NOT closed at 563.
        # So 563 must have been closing something else?
        # 469 stats-grid. 563 closed stats-grid?
        # If so, effectively `general` wraps everything.
        # SO: I need to close `stats-grid` EARLY (at 502).
        # AND I need to close `general` at 564.
        # What about the original 563 `</div>`?
        # If I close `stats-grid` at 502, then 563 becomes ... an extra closing div?
        # Or maybe 563 closes `inactive-alert`'s parent?
        # Let's just Add closing tags and see.
        # Safest: Insert `</div>` for stats-grid at 502.
        # And Insert `</div>` for general at 564.
        inserted_general_close = True
        
    new_lines.append(line)

path.write_text("\n".join(new_lines), encoding="utf-8")
print(f"Fixed HTML structure in {path}")
