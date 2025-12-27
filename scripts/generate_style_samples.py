
import xlsxwriter
import random
from datetime import datetime
import os

def generate_samples():
    filename = "style_samples.xlsx"
    workbook = xlsxwriter.Workbook(filename)
    
    # Dummy Data
    data = [
        {"Name": "Player_One", "Rank": "Owner", "Total Msgs": 15420, "XP Year": 150000000, "Boss Year": 5000},
        {"Name": "Iron_Meme", "Rank": "Deputy", "Total Msgs": 8200, "XP Year": 89000000, "Boss Year": 1200},
        {"Name": "PvM_God", "Rank": "Admin", "Total Msgs": 4100, "XP Year": 210000000, "Boss Year": 8500},
        {"Name": "Skiller_Pro", "Rank": "Member", "Total Msgs": 3200, "XP Year": 45000000, "Boss Year": 10},
        {"Name": "Noob_Slayer", "Rank": "Member", "Total Msgs": 1500, "XP Year": 12000000, "Boss Year": 350},
        {"Name": "Lurker_Steve", "Rank": "Member", "Total Msgs": 50, "XP Year": 5000000, "Boss Year": 0},
        {"Name": "Inactive_Bob", "Rank": "Member", "Total Msgs": 0, "XP Year": 0, "Boss Year": 0},
    ]

    # --- SHARED FUNDAMENTALS ---
    # User Preferences: 1A (Dark/Neon), 2B (Glowing Header), 3A/D (Zebra + Icons)
    
    # ==========================================
    # SAMPLE 1: NEON NIGHTS (Deep Cyberpunk)
    # ==========================================
    ws1 = workbook.add_worksheet("1. Neon Nights")
    fmt_1_header = workbook.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#000000',
        'bottom': 5, 'bottom_color': '#00FFFF', # Glowing effect
        'align': 'center', 'valign': 'vcenter', 'font_size': 12
    })
    fmt_1_odd = workbook.add_format({'bg_color': '#111111', 'font_color': '#E0E0E0', 'border': 0})
    fmt_1_even = workbook.add_format({'bg_color': '#1a1a1a', 'font_color': '#E0E0E0', 'border': 0})
    fmt_1_border = workbook.add_format({'bottom': 1, 'bottom_color': '#333333'}) # Subtle row separator

    create_sample_sheet(ws1, data, fmt_1_header, fmt_1_odd, fmt_1_even, "Neon Nights: Pure Black + Cyan Glow")

    # ==========================================
    # SAMPLE 2: OSRS DARK (Thematic)
    # ==========================================
    ws2 = workbook.add_worksheet("2. OSRS Dark")
    fmt_2_header = workbook.add_format({
        'bold': True, 'font_color': '#FFD700', 'bg_color': '#2b2b2b', # Stone Gray
        'bottom': 5, 'bottom_color': '#FF0000', # Dragon Red Glow
        'align': 'center', 'valign': 'vcenter', 'font_size': 12, 'font_name': 'Constantia'
    })
    fmt_2_odd = workbook.add_format({'bg_color': '#383838', 'font_color': '#FFD700', 'font_name': 'Constantia'})
    fmt_2_even = workbook.add_format({'bg_color': '#404040', 'font_color': '#FFD700', 'font_name': 'Constantia'})
    
    create_sample_sheet(ws2, data, fmt_2_header, fmt_2_odd, fmt_2_even, "OSRS Dark: Stone + Gold + Red")

    # ==========================================
    # SAMPLE 3: TOXIC WASTE (Vibrant Green)
    # ==========================================
    ws3 = workbook.add_worksheet("3. Toxic Waste")
    fmt_3_header = workbook.add_format({
        'bold': True, 'font_color': '#00FF00', 'bg_color': '#051005',
        'bottom': 5, 'bottom_color': '#8800FF', # Purple Glow
        'align': 'center', 'valign': 'vcenter', 'font_size': 12
    })
    fmt_3_odd = workbook.add_format({'bg_color': '#0a1a0a', 'font_color': '#ccffcc'})
    fmt_3_even = workbook.add_format({'bg_color': '#0f240f', 'font_color': '#ccffcc'})

    create_sample_sheet(ws3, data, fmt_3_header, fmt_3_odd, fmt_3_even, "Toxic Waste: Deep Green + Purple")

    # ==========================================
    # SAMPLE 4: STEALTH BLACK (Minimalist)
    # ==========================================
    ws4 = workbook.add_worksheet("4. Stealth Black")
    fmt_4_header = workbook.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#121212',
        'bottom': 2, 'bottom_color': '#444444', # Subtle Glow
        'align': 'center', 'valign': 'vcenter', 'font_size': 11
    })
    fmt_4_odd = workbook.add_format({'bg_color': '#181818', 'font_color': '#BBBBBB'})
    fmt_4_even = workbook.add_format({'bg_color': '#202020', 'font_color': '#BBBBBB'})

    create_sample_sheet(ws4, data, fmt_4_header, fmt_4_odd, fmt_4_even, "Stealth: Matte Black + Soft White (Low Eye Strain)")

    # ==========================================
    # SAMPLE 5: ROYAL MIDNIGHT (Deep Navy)
    # ==========================================
    ws5 = workbook.add_worksheet("5. Royal Midnight")
    fmt_5_header = workbook.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#05051a',
        'bottom': 5, 'bottom_color': '#00BFFF', # Deep Sky Blue
        'align': 'center', 'valign': 'vcenter', 'font_size': 12
    })
    fmt_5_odd = workbook.add_format({'bg_color': '#0a0a24', 'font_color': '#dceeff'})
    fmt_5_even = workbook.add_format({'bg_color': '#101030', 'font_color': '#dceeff'})

    create_sample_sheet(ws5, data, fmt_5_header, fmt_5_odd, fmt_5_even, "Royal Midnight: Navy + Silver")

    workbook.close()
    print(f"Generated {filename}")

def create_sample_sheet(ws, data, fmt_header, fmt_odd, fmt_even, description):
    headers = list(data[0].keys())
    
    # Write Description
    ws.write(0, 0, description)
    
    # Write Headers
    for c, h in enumerate(headers):
        ws.write(2, c, h, fmt_header)
        ws.set_column(c, c, 18)

    # Write Data
    for r, row in enumerate(data):
        r_idx = r + 3
        fmt = fmt_even if r % 2 == 0 else fmt_odd
        
        # Add Icon for Rank 1 (Simulated logic)
        name_val = row['Name']
        if r == 2: # PvM God
            name_val = "⚔️ " + name_val
        if r == 0: # Player One
             name_val = "👑 " + name_val

        ws.write(r_idx, 0, name_val, fmt)
        ws.write(r_idx, 1, row['Rank'], fmt)
        ws.write(r_idx, 2, row['Total Msgs'], fmt)
        ws.write(r_idx, 3, f"{row['XP Year']:,}", fmt)
        ws.write(r_idx, 4, f"{row['Boss Year']:,}", fmt)
    
    ws.hide_gridlines(2)

if __name__ == "__main__":
    generate_samples()
