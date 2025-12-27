import xlsxwriter
import datetime

def create_sample_workbook():
    filename = "boss_color_samples.xlsx"
    workbook = xlsxwriter.Workbook(filename)
    
    # Base "Neon Glow" Theme constants (Fixed)
    BG_DARK = '#121212'
    TEXT_WHITE = '#E0E0E0'
    BORDER_GREY = '#444444'
    
    BG_ZERO = '#4d0000'
    TEXT_ZERO = '#ffcccc'
    
    # Options to present
    options = [
        ("1. Neon Purple",  '#2a0a2a', '#3e1a3e', '#d000ff'), # Deep Purple BG, Neon Purple Text
        ("2. Hot Pink",     '#2a0a1a', '#3e1a2a', '#ff0080'), # Deep Pink BG, Hot Pink Text
        ("3. Toxic Orange", '#2a1a0a', '#3e261a', '#ffaa00'), # Deep Orange BG, Neon Orange Text
        ("4. Cyber Teal",   '#0a2a2a', '#1a3e3e', '#00ffd5'), # Deep Teal BG, Neon Teal Text
        ("5. Sterling Silver", '#1a1a1a', '#2a2a2a', '#ffffff'), # Neutral Grey BG, White Text (Max Zero Pop)
    ]
    
    # Dummy Data
    data = [
        ["User A", 1500, 0, 10],   # Has kills
        ["User B", 0, 0, 0],       # Zero
        ["User C", 500, 0, 5],     # Has kills
        ["User D", 0, 0, 0],       # Zero
        ["User E", 25000, 0, 150], # Big kills
    ]
    
    base_fmt_props = {
        'font_name': 'Inter',
        'font_size': 10,
        'font_color': TEXT_WHITE,
        'bg_color': BG_DARK,
        'border': 1,
        'border_color': BORDER_GREY,
        'valign': 'vcenter'
    }
    
    fmt_zero_props = base_fmt_props.copy()
    fmt_zero_props.update({'bg_color': BG_ZERO, 'font_color': TEXT_ZERO, 'bold': True, 'align': 'center'})
    fmt_zero = workbook.add_format(fmt_zero_props)
    
    fmt_base = workbook.add_format(base_fmt_props)

    for name, bg_odd, bg_even, text_color in options:
        worksheet = workbook.add_worksheet(name[:30]) # Excel limit
        
        # Create Formats for this option
        f_odd = workbook.add_format(base_fmt_props)
        f_odd.set_bg_color(bg_odd)
        f_odd.set_font_color(text_color)
        
        f_even = workbook.add_format(base_fmt_props)
        f_even.set_bg_color(bg_even)
        f_even.set_font_color(text_color)
        
        # Headers
        worksheet.write(0, 0, "Name", fmt_base)
        worksheet.write(0, 1, "XP (Green)", fmt_base)
        worksheet.write(0, 2, "Boss (Previous)", fmt_base) # Just a spacer
        worksheet.write(0, 3, f"Boss ({name})", fmt_base)
        
        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 3, 15)
        
        for i, row in enumerate(data):
            r = i + 1
            is_even = (i % 2 == 0)
            fmt = f_even if is_even else f_odd
            
            # Name
            worksheet.write(r, 0, row[0], fmt_base)
            
            # XP (Static Green)
            worksheet.write(r, 1, 10000, fmt_base) 
            
            # Boss Value
            val = row[3]
            
            cell_fmt = fmt
            if val == 0:
                cell_fmt = fmt_zero
            
            worksheet.write(r, 3, val, cell_fmt)
            
    workbook.close()
    print(f"Generated {filename}")

if __name__ == "__main__":
    create_sample_workbook()
