import requests
import os

BASE_URL = "https://oldschool.runescape.wiki"
DEST_DIR = "e:/Clan_activity_report/assets"
HEADERS = {
    "User-Agent": "AntigravityBot/1.0 (internal tool)"
}

def download_file(url, filename):
    filepath = os.path.join(DEST_DIR, filename)
    try:
        print(f"Trying {url} -> {filename}")
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(res.content)
            print(f"Success: {filename}")
            return True
        else:
            print(f"Failed: {res.status_code}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# Manual Fixes
fixes = [
    # Ranks
    {"name": "rank_deputy_owner.png", "urls": [
        f"{BASE_URL}/images/Clan_icon_-_Deputy_owner.png", 
        f"{BASE_URL}/images/Clan_icon_-_Deputy_Owner.png"
    ]},
    {"name": "rank_advisor.png", "urls": [
        f"{BASE_URL}/images/Clan_icon_-_Advisor.png",
        f"{BASE_URL}/images/Clan_icon_-_Council.png" # Sometimes called Council?
    ]},
    {"name": "rank_topaz.png", "urls": [f"{BASE_URL}/images/Clan_icon_-_Topaz.png"]},
    
    # Bosses
    {"name": "boss_zulrah.png", "urls": [
        f"{BASE_URL}/images/Zulrah_chathead.png",
        f"{BASE_URL}/images/Zulrah_(Serpentine)_chathead.png",
        f"{BASE_URL}/images/Zulrah.png",
        f"{BASE_URL}/images/Zulrah_(Serpentine).png"
    ]},
    {"name": "boss_mimic.png", "urls": [
        f"{BASE_URL}/images/The_Mimic_chathead.png",
        f"{BASE_URL}/images/Mimic_chathead.png"
    ]},
    {"name": "boss_hespori.png", "urls": [
        f"{BASE_URL}/images/Hespori_chathead.png"
    ]}
]

def main():
    for item in fixes:
        filename = item["name"]
        if os.path.exists(os.path.join(DEST_DIR, filename)):
            print(f"Exists: {filename}")
            continue
            
        for url in item["urls"]:
            if download_file(url, filename):
                break

if __name__ == "__main__":
    main()
