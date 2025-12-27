
import os
import shutil
import sys
from rich.console import Console

console = Console()

def publish_to_docs():
    console.print("[bold cyan]🚀 Starting GitHub Pages Deployment (Publish to /docs)...[/bold cyan]")
    
    root_dir = os.getcwd()
    docs_dir = os.path.join(root_dir, "docs")
    
    # 1. Ensure docs directory exists
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        console.print(f"[green]Created directory: {docs_dir}[/green]")
    
    # 2. Clean docs directory (Safety: Only delete specific known files/folders to avoid blowing up .git if someone initialized there)
    # Actually, standard practice is to wipe it or overwrite. Let's overwrite.
    # Warning: If docs/CNAME exists, keep it.
    
    # List of files/folders to copy
    files_to_copy = {
        "clan_dashboard.html": "index.html", # RENAME to index.html
        "dashboard_logic.js": "dashboard_logic.js",
        "clan_data.js": "clan_data.js", # Data file
        "ai_data.js": "ai_data.js",   # AI Data file
        "clan_data.json": "clan_data.json", # Raw JSON (if needed by JS)
    }
    
    dirs_to_copy = ["assets"]
    
    # Copy Files
    for src, dst in files_to_copy.items():
        src_path = os.path.join(root_dir, src)
        dst_path = os.path.join(docs_dir, dst)
        
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            console.print(f"  ✅ Copied [bold]{src}[/bold] -> docs/{dst}")
        else:
            console.print(f"  ❌ Missing Source: {src}", style="bold red")

    # Copy Directories
    for d in dirs_to_copy:
        src_dir = os.path.join(root_dir, d)
        dst_dir = os.path.join(docs_dir, d)
        
        if os.path.exists(src_dir):
            if os.path.exists(dst_dir):
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir)
            console.print(f"  ✅ Copied Folder [bold]{d}[/bold] -> docs/{d}")
        else:
            console.print(f"  ❌ Missing Source Folder: {d}", style="bold red")

    console.print("\n[bold green]✨ Deployment Ready![/bold green]")
    console.print("To go live: [bold white]git add docs && git commit -m 'Deploy Dashboard' && git push[/bold white]")

if __name__ == "__main__":
    publish_to_docs()
