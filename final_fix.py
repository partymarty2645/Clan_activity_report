import requests
import os

BASE_URL = "https://oldschool.runescape.wiki/images"
DEST_DIR = "e:/Clan_activity_report/assets"
HEADERS = {
    "User-Agent": "AntigravityBot/1.0"
}

attempts = [
    ("rank_advisor.png", ["Clan_icon_-_Advisor.png", "Clan_icon_-_Councillor.png", "Clan_icon_-_Council.png", "Clan_icon_-_Counsellor.png"]),
    ("rank_topaz.png", ["Clan_icon_-_Topaz.png", "Clan_icon_-_Topaz_member.png", "Clan_icon_-_Topaz_rank.png"])
]

def try_download():
    for filename, urls in attempts:
        if os.path.exists(os.path.join(DEST_DIR, filename)):
            print(f"Already have {filename}")
            continue

        for url_suffix in urls:
            url = f"{BASE_URL}/{url_suffix}"
            try:
                res = requests.get(url, headers=HEADERS)
                if res.status_code == 200:
                    with open(os.path.join(DEST_DIR, filename), 'wb') as f:
                        f.write(res.content)
                    print(f"Success: {filename} from {url_suffix}")
                    break
                else:
                    pass # Silent fail
            except:
                pass
        else:
            print(f"Given up on {filename}")

if __name__ == "__main__":
    try_download()
