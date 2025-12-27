
import xlsxwriter
import random

def generate_samples_v2():
    filename = "style_samples_v2.xlsx"
    workbook = xlsxwriter.Workbook(filename)
    
    # Dummy Data
    data = [
        {"Name": "Player_One", "Rank": "Owner", "Total Msgs": 15420, "XP Year": 150000000, "Boss Year": 5000},
        {"Name": "Iron_Meme", "Rank": "Deputy", "Total Msgs": 8200, "XP Year": 89000000, "Boss Year": 1200},
        {"Name": "PvM_God", "Rank": "Admin", "Total Msgs": 4100, "XP Year": 210000000, "Boss Year": 8500},
        {"Name": "Skiller_Pro", "Rank": "Member", "Total Msgs": 3200, "XP Year": 45000000, "Boss Year": 10},
        {"Name": "Noob_Slayer", "Rank": "Member", "Total Msgs": 1500, "XP Year": 12000000, "Boss Year": 350},
    ]

    # DATA TYPES:
    # 1. Identity (Name/Rank) -> Gray/Neutral
    # 2. Messages -> Blue
    # 3. XP -> Green
    # 4. Boss -> Red

    # ==========================================
    # VARIATION 1: NEON GLOW (The current implementation idea)
    # Deep Black background with vibrant, glowing text/borders
    # ==========================================
    ws1 = workbook.add_worksheet("1. Neon Glow")
    create_sample_sheet(ws1, workbook, data, {
        'id_bg': '#121212', 'id_txt': '#E0E0E0', 'id_bd': '#444444',
        'msg_bg': '#05051a', 'msg_txt': '#00FFFF', 'msg_bd': '#00BFFF',
        'xp_bg': '#051405', 'xp_txt': '#00FF00', 'xp_bd': '#00FF00',
        'boss_bg': '#1a0505', 'boss_txt': '#FF3333', 'boss_bd': '#FF0000',
        'desc': "1. Neon Glow: Deep black backgrounds with bright, glowing neon text for each category."
    })

    # ==========================================
    # VARIATION 2: PASTEL SOFT (Easier on eyes)
    # Lighter/Softer backgrounds, darker text
    # ==========================================
    ws2 = workbook.add_worksheet("2. Pastel Soft")
    create_sample_sheet(ws2, workbook, data, {
        'id_bg': '#2e2e30', 'id_txt': '#ffffff', 'id_bd': '#555555',
        'msg_bg': '#202040', 'msg_txt': '#bfdfff', 'msg_bd': '#6b8cbd', # Soft Blue
        'xp_bg': '#203020', 'xp_txt': '#cfffcf', 'xp_bd': '#7bc97b', # Soft Green
        'boss_bg': '#302020', 'boss_txt': '#ffcfcf', 'boss_bd': '#c97b7b', # Soft Red
        'desc': "2. Pastel Soft: Muted, softer colors that are less harsh but still distinct."
    })

    # ==========================================
    # VARIATION 3: HIGH CONTRAST BLOCKS
    # Very distinct solid background blocks
    # ==========================================
    ws3 = workbook.add_worksheet("3. Color Blocks")
    create_sample_sheet(ws3, workbook, data, {
        'id_bg': '#404040', 'id_txt': '#FFFFFF', 'id_bd': '#000000',
        'msg_bg': '#003366', 'msg_txt': '#FFFFFF', 'msg_bd': '#000000', # Solid Dark Blue
        'xp_bg': '#004d00', 'xp_txt': '#FFFFFF', 'xp_bd': '#000000', # Solid Dark Green
        'boss_bg': '#660000', 'boss_txt': '#FFFFFF', 'boss_bd': '#000000', # Solid Dark Red
        'desc': "3. Color Blocks: Solid, distinct background colors for each section. Very clear separation."
    })

    # ==========================================
    # VARIATION 4: MINIMALIST (Text Only)
    # Black background, only the text is colored
    # ==========================================
    ws4 = workbook.add_worksheet("4. Text Only")
    create_sample_sheet(ws4, workbook, data, {
        'id_bg': '#000000', 'id_txt': '#888888', 'id_bd': '#222222',
        'msg_bg': '#000000', 'msg_txt': '#3399FF', 'msg_bd': '#222222',
        'xp_bg': '#000000', 'xp_txt': '#33FF33', 'xp_bd': '#222222',
        'boss_bg': '#000000', 'boss_txt': '#FF3333', 'boss_bd': '#222222',
        'desc': "4. Text Only: Pure black background everywhere. Only the text color indicates the category."
    })

    # ==========================================
    # VARIATION 5: GRADIENT HEADERS
    # Neutral body, but intense headers
    # ==========================================
    ws5 = workbook.add_worksheet("5. Header Focus")
    create_sample_sheet(ws5, workbook, data, {
        'id_bg': '#1a1a1a', 'id_txt': '#bbbbbb', 'id_bd': '#333333',
        'msg_bg': '#1a1a1a', 'msg_txt': '#bbbbbb', 'msg_bd': '#333333',
        'xp_bg': '#1a1a1a', 'xp_txt': '#bbbbbb', 'xp_bd': '#333333',
        'boss_bg': '#1a1a1a', 'boss_txt': '#bbbbbb', 'boss_bd': '#333333',
        'desc': "5. Header Focus: The data rows are neutral gray. Only the HEADERS (Row 1) use the distinct colors."
    })


    workbook.close()
    print(f"Generated {filename}")

def create_sample_sheet(ws, wb, data, colors):
    headers = list(data[0].keys())
    
    ws.write(0, 0, colors.get('desc', ''))
    
    # -- FORMATS --
    base = {'border': 1, 'align': 'center', 'valign': 'vcenter'}
    
    # Headers
    fmt_h_id = wb.add_format({**base, 'bold': True, 'bg_color': '#000000', 'font_color': colors['id_bd'], 'bottom': 2, 'bottom_color': colors['id_bd']})
    fmt_h_msg = wb.add_format({**base, 'bold': True, 'bg_color': '#000000', 'font_color': colors['msg_bd'], 'bottom': 2, 'bottom_color': colors['msg_bd']})
    fmt_h_xp = wb.add_format({**base, 'bold': True, 'bg_color': '#000000', 'font_color': colors['xp_bd'], 'bottom': 2, 'bottom_color': colors['xp_bd']})
    fmt_h_boss = wb.add_format({**base, 'bold': True, 'bg_color': '#000000', 'font_color': colors['boss_bd'], 'bottom': 2, 'bottom_color': colors['boss_bd']})

    # Data
    fmt_d_id = wb.add_format({**base, 'bg_color': colors['id_bg'], 'font_color': colors['id_txt'], 'border_color': colors['id_bd']})
    fmt_d_msg = wb.add_format({**base, 'bg_color': colors['msg_bg'], 'font_color': colors['msg_txt'], 'border_color': colors['msg_bd']})
    fmt_d_xp = wb.add_format({**base, 'bg_color': colors['xp_bg'], 'font_color': colors['xp_txt'], 'border_color': colors['xp_bd']})
    fmt_d_boss = wb.add_format({**base, 'bg_color': colors['boss_bg'], 'font_color': colors['boss_txt'], 'border_color': colors['boss_bd']})

    # -- WRITE --
    row_off = 2
    for c, col_name in enumerate(headers):
        # Select Header Format
        if 'Msg' in col_name: fmt = fmt_h_msg
        elif 'XP' in col_name: fmt = fmt_h_xp
        elif 'Boss' in col_name: fmt = fmt_h_boss
        else: fmt = fmt_h_id
        
        ws.write(row_off, c, col_name, fmt)
        ws.set_column(c, c, 18)

    for r, row in enumerate(data):
        curr_row = row_off + 1 + r
        
        # Name Decoration
        name_val = row['Name']
        if r == 0: name_val = "👑 " + name_val
        if r == 1: name_val = "🥈 " + name_val

        for c, col_name in enumerate(headers):
            val = name_val if col_name == 'Name' else row[col_name]
            
            # Select Data Format
            if 'Msg' in col_name: fmt = fmt_d_msg
            elif 'XP' in col_name: fmt = fmt_d_xp
            elif 'Boss' in col_name: fmt = fmt_d_boss
            else: fmt = fmt_d_id

            if isinstance(val, int):
                val = f"{val:,}"

            ws.write(curr_row, c, val, fmt)
            
    ws.hide_gridlines(2)

if __name__ == "__main__":
    generate_samples_v2()
