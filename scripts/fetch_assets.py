
import os
import requests
from rich.console import Console

console = Console()

ASSETS_DIR = r"D:\Clan_activity_report\assets"
BASE_URL = "https://oldschool.runescape.wiki/images"

# Mapping: Wiki Filename -> Local Filename
# Note: Wiki filenames are case-sensitive and use underscores.
TARGETS = {
    "Verac_the_Defiled.png": "boss_verac_the_defiled.png",
    "Torag_the_Corrupted.png": "boss_torag_the_corrupted.png",
    "Karil_the_Tainted.png": "boss_karil_the_tainted.png",
    "Guthan_the_Infested.png": "boss_guthan_the_infested.png",
    "Dharok_the_Wretched.png": "boss_dharok_the_wretched.png",
    "Ahrim_the_Blighted.png": "boss_ahrim_the_blighted.png",
    "Sol_Heredit.png": "boss_sol_heredit.png",
    "Deranged_archaeologist.png": "boss_deranged_archaeologist.png",
    "Crazy_archaeologist.png": "boss_crazy_archaeologist.png"
}

def fetch_assets():
    console.print(f"[cyan]Downloading {len(TARGETS)} missing assets to {ASSETS_DIR}...[/cyan]")
    
    headers = {
        'User-Agent': 'ClanActivityReport/1.0 (contact: admin@example.com)'
    }

    success_count = 0
    
    for wiki_name, local_name in TARGETS.items():
        url = f"{BASE_URL}/{wiki_name}"
        save_path = os.path.join(ASSETS_DIR, local_name)
        
        try:
            console.print(f"Fetching [bold]{wiki_name}[/bold]...", end=" ")
            resp = requests.get(url, headers=headers)
            
            if resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(resp.content)
                console.print(f"[green]OK[/green] -> {local_name}")
                success_count += 1
            else:
                console.print(f"[red]FAILED ({resp.status_code})[/red]")
                
        except Exception as e:
            console.print(f"[red]ERROR: {e}[/red]")

    console.print(f"\n[green]Finished! Downloaded {success_count}/{len(TARGETS)} assets.[/green]")

if __name__ == "__main__":
    fetch_assets()
