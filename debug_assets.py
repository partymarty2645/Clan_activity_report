import requests
from bs4 import BeautifulSoup
import os

HEADERS = {
    "User-Agent": "AntigravityBot/1.0 (internal tool)"
}
DEST_DIR = "e:/Clan_activity_report/assets"

targets = [
    {"name": "rank_advisor.png", "page": "https://oldschool.runescape.wiki/w/File:Clan_icon_-_Advisor.png"},
    {"name": "boss_zulrah.png", "page": "https://oldschool.runescape.wiki/w/File:Zulrah_(serpentine).png"},
    {"name": "rank_topaz.png", "page": "https://oldschool.runescape.wiki/w/File:Clan_icon_-_Topaz.png"}
]

def download_from_file_page(name, url):
    print(f"Checking {url}...")
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # The main image usually has class "internal" or is in a div "fullMedia"
        # Look for the link closest to "Original file"
        
        # Option 1: div class="fullMedia" -> a -> href
        div = soup.find("div", {"class": "fullMedia"})
        if div:
            a = div.find("a")
            if a:
                img_url = a.get("href")
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = "https://oldschool.runescape.wiki" + img_url
                    
                print(f"Found URL: {img_url}")
                # Download
                r_img = requests.get(img_url, headers=HEADERS)
                if r_img.status_code == 200:
                    with open(os.path.join(DEST_DIR, name), 'wb') as f:
                        f.write(r_img.content)
                    print(f"Downloaded {name}")
                    return
        
        print(f"Could not find image link for {name}")

    except Exception as e:
        print(f"Error {name}: {e}")

if __name__ == "__main__":
    for t in targets:
        download_from_file_page(t["name"], t["page"])
