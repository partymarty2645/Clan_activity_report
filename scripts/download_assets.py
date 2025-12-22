import os
import json
import asyncio
import aiohttp
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

console = Console()

ASSET_CONFIG_FILE = os.path.join(os.getcwd(), 'assets', 'asset_list.json')
TARGET_DIR = os.path.join(os.getcwd(), 'assets')

def normalize_name(name):
    # "Red Topaz" -> "rank_red_topaz.png" (clean name)
    clean = name.lower().replace(" ", "_").replace("-", "_")
    return f"rank_{clean}.png"

async def download_file(session, url, filepath, name, progress, task_id):
    if os.path.exists(filepath):
        progress.advance(task_id)
        return
    
    try:
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                content = await response.read()
                with open(filepath, 'wb') as f:
                    f.write(content)
            else:
                console.print(f"[red]Failed to download {name}: Status {response.status}[/red]")
    except Exception as e:
        console.print(f"[red]Error downloading {name}: {e}[/red]")
    finally:
        progress.advance(task_id)

async def download_assets_async():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        
    if not os.path.exists(ASSET_CONFIG_FILE):
        console.print(f"[bold red]Config file not found: {ASSET_CONFIG_FILE}[/bold red]")
        return

    with open(ASSET_CONFIG_FILE, 'r') as f:
        rank_data = json.load(f)

    console.print(f"[cyan]Starting download of {len(rank_data)} assets...[/cyan]")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task("[green]Downloading Assets...", total=len(rank_data))
            
            tasks = []
            for item in rank_data:
                name = item['name']
                url = item['url']
                filename = normalize_name(name)
                filepath = os.path.join(TARGET_DIR, filename)
                tasks.append(download_file(session, url, filepath, name, progress, task_id))
            
            await asyncio.gather(*tasks)

    console.print(f"[bold green]Finished asset download process.[/bold green]")

if __name__ == "__main__":
    asyncio.run(download_assets_async())


