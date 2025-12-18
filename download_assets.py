import requests
import os
import time
from bs4 import BeautifulSoup
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://oldschool.runescape.wiki"
DEST_DIR = "e:/Clan_activity_report/assets"
HEADERS = {
    "User-Agent": "AntigravityBot/1.0 (internal tool developed for OSRS fan project)"
}

if not os.path.exists(DEST_DIR):
    os.makedirs(DEST_DIR)

URL_Overrides_Map = {
    # Ranks
    "Deputy_Owner": [
        f"{BASE_URL}/images/Clan_icon_-_Deputy_owner.png", # Lowercase 'o' verified
        f"{BASE_URL}/images/Clan_icon_-_Deputy_Owner.png",
    ],
    "Advisor": [
        f"{BASE_URL}/images/Clan_icon_-_Advisor.png",
        f"{BASE_URL}/images/Clan_icon_-_Councillor.png",
    ],
    
    # Bosses
    "Zulrah": [
        f"{BASE_URL}/images/Zulrah_(serpentine).png",
        f"{BASE_URL}/images/Zulrah.png",
    ],
    "Thermonuclear_Smoke_Devil": [f"{BASE_URL}/images/Thermonuclear_smoke_devil.png"],
    "Giant_Mole": [f"{BASE_URL}/images/Giant_Mole.png"], 
    "Deranged_Archaeologist": [f"{BASE_URL}/images/Deranged_Archaeologist.png"],
}

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def download_file(url, filename):
    filepath = os.path.join(DEST_DIR, filename)
    # Overwrite enabled to ensure we get the latest
    
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(res.content)
            # print(f"Downloaded: {filename}")
            return True
        else:
            print(f"Failed to download {filename} from {url} (Status: {res.status_code})")
            return False
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False

def fetch_skills():
    print("Fetching Skills...")
    # Standard list is safer and sufficient for OSRS (23 skills)
    target_skills = [
        "Attack", "Strength", "Defence", "Ranged", "Prayer", "Magic", "Runecraft", "Hitpoints",
        "Crafting", "Mining", "Smithing", "Fishing", "Cooking", "Firemaking", "Woodcutting",
        "Agility", "Herblore", "Thieving", "Fletching", "Slayer", "Farming", "Construction", "Hunter"
    ]
    
    for skill in target_skills:
        # Try standard icon URL
        url = f"{BASE_URL}/images/{skill}_icon.png"
        filename = f"skill_{skill.lower()}.png"
        if not download_file(url, filename):
             print(f"Failed to fetch skill: {skill}")

def fetch_bosses():
    print("Fetching Bosses...")
    soup = get_soup("https://oldschool.runescape.wiki/w/Boss")
    if not soup:
        return

    boss_names = set()
    # Scrape tables with class 'wikitable'
    tables = soup.find_all('table', {'class': 'wikitable'})
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            # Check th and td entries for links
            cells = row.find_all(['th', 'td'])
            for cell in cells:
                link = cell.find('a')
                if link and link.get('title'):
                    title = link.get('title')
                    # Filter out non-boss links loosely if possible, but title usually is the boss name
                    # We accept most links in these tables
                    boss_names.add(title)

    print(f"Found {len(boss_names)} potential bosses.")
    
    # Process each boss
    for boss in boss_names:
        safe_name = boss.replace(" ", "_")
        
        # 0. Check overrides
        if safe_name in URL_Overrides_Map or boss in URL_Overrides_Map:
            key = safe_name if safe_name in URL_Overrides_Map else boss
            success = False
            for url in URL_Overrides_Map[key]:
                 if download_file(url, f"boss_{safe_name.lower()}.png"):
                     success = True
                     break
            if success:
                continue

        # 1. Try chathead (preferred)
        url_chathead = f"{BASE_URL}/images/{safe_name}_chathead.png"
        filename = f"boss_{safe_name.lower()}.png"
        
        if download_file(url_chathead, filename):
            continue
            
        # 2. Try removing "The_" prefix
        if safe_name.startswith("The_"):
            safe_name_no_the = safe_name[4:]
            url_chathead_2 = f"{BASE_URL}/images/{safe_name_no_the}_chathead.png"
            if download_file(url_chathead_2, filename):
                continue

        # 3. Try plain image
        url_plain = f"{BASE_URL}/images/{safe_name}.png"
        if download_file(url_plain, filename):
            continue

        # 4. Try parsing redirect or checking if page exists? No, too complex.
        # Just log failure.
        # print(f"Could not download image for boss: {boss}")

def fetch_ranks():
    print("Fetching Ranks...")
    # Standard Clan Ranks + Gems
    ranks = [
        "Owner", "Deputy_Owner", "Administrator", "Moderator", "Advisor",
        "Captain", "General", "Lieutenant", "Sergeant", "Corporal", "Recruit",
        "Dragonstone", "Diamond", "Ruby", "Emerald", "Sapphire", "Topaz", "Jade", "Opal"
    ]
    
    for rank in ranks:
        urls_to_try = []
        if rank in URL_Overrides_Map:
            urls_to_try = URL_Overrides_Map[rank]
        else:
            urls_to_try.append(f"{BASE_URL}/images/Clan_icon_-_{rank}.png")

        filename = f"rank_{rank.lower()}.png"
        
        success = False
        for url in urls_to_try:
            if download_file(url, filename):
                success = True
                break
        
        if not success:
            # Fallback for Gems? Maybe 'Clan_icon_-_Dragonstone.png' works?
            # It should.
            print(f"Failed rank: {rank}")

def main():
    print("Starting asset download...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        futures.append(executor.submit(fetch_skills))
        futures.append(executor.submit(fetch_bosses))
        futures.append(executor.submit(fetch_ranks))
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Job failed: {e}")
                
    print("Download complete.")

if __name__ == "__main__":
    main()
