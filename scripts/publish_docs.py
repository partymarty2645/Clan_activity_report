
import os
import shutil
import sys
from datetime import datetime
from rich.console import Console

console = Console()


def sync_dashboard_files():
    """Keep root and docs dashboard copies identical by copying the newer file over the older."""
    root_dashboard = "dashboard_logic.js"
    docs_dashboard = os.path.join("docs", "dashboard_logic.js")

    # If only one exists, clone it to the missing location
    if os.path.exists(root_dashboard) and not os.path.exists(docs_dashboard):
        os.makedirs(os.path.dirname(docs_dashboard), exist_ok=True)
        shutil.copy2(root_dashboard, docs_dashboard)
        console.print("[yellow]Synced dashboard root -> docs (docs copy missing)[/yellow]")
        return
    if os.path.exists(docs_dashboard) and not os.path.exists(root_dashboard):
        shutil.copy2(docs_dashboard, root_dashboard)
        console.print("[yellow]Synced dashboard docs -> root (root copy missing)[/yellow]")
        return

    if not os.path.exists(root_dashboard) or not os.path.exists(docs_dashboard):
        return

    root_time = os.path.getmtime(root_dashboard)
    docs_time = os.path.getmtime(docs_dashboard)
    if docs_time > root_time:
        shutil.copy2(docs_dashboard, root_dashboard)
        console.print("[yellow]Synced dashboard docs -> root (docs newer)[/yellow]")
    elif root_time > docs_time:
        shutil.copy2(root_dashboard, docs_dashboard)
        console.print("[yellow]Synced dashboard root -> docs (root newer)[/yellow]")


def sync_dashboard_html():
    """Keep root HTML (clan_dashboard.html) and docs index.html in sync based on mtime."""
    root_html = "clan_dashboard.html"
    docs_html = os.path.join("docs", "index.html")

    # Ensure docs directory exists for copy targets
    os.makedirs(os.path.dirname(docs_html), exist_ok=True)

    if os.path.exists(root_html) and not os.path.exists(docs_html):
        shutil.copy2(root_html, docs_html)
        console.print("[yellow]Synced dashboard HTML root -> docs (docs copy missing)[/yellow]")
        return
    if os.path.exists(docs_html) and not os.path.exists(root_html):
        shutil.copy2(docs_html, root_html)
        console.print("[yellow]Synced dashboard HTML docs -> root (root copy missing)[/yellow]")
        return
    if not os.path.exists(root_html) or not os.path.exists(docs_html):
        return

    root_time = os.path.getmtime(root_html)
    docs_time = os.path.getmtime(docs_html)
    if docs_time > root_time:
        shutil.copy2(docs_html, root_html)
        console.print("[yellow]Synced dashboard HTML docs -> root (docs newer)[/yellow]")
    elif root_time > docs_time:
        shutil.copy2(root_html, docs_html)
        console.print("[yellow]Synced dashboard HTML root -> docs (root newer)[/yellow]")

def publish_to_docs():
    console.print("[bold cyan]🚀 Starting GitHub Pages Deployment (Publish to /docs)...[/bold cyan]")
    
    root_dir = os.getcwd()
    docs_dir = os.path.join(root_dir, "docs")
    
    # Keep dashboard files in sync before copying anything else
    sync_dashboard_files()
    
    # 1. Ensure docs directory exists
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        console.print(f"[green]Created directory: {docs_dir}[/green]")
    
    # Keep dashboard JS/HTML in sync before copying anything else
    sync_dashboard_files()
    sync_dashboard_html()

    # 2. Clean docs directory (Safety: Only delete specific known files/folders to avoid blowing up .git if someone initialized there)
    # Actually, standard practice is to wipe it or overwrite. Let's overwrite.
    # Warning: If docs/CNAME exists, keep it.
    
    # List of files/folders to copy (dashboard already synced both ways)
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

    # Success message
    console.print("[bold green]✨ Deployment Ready![/bold green]")
    
    console.print("To go live: [bold white]git add docs && git commit -m 'Deploy Dashboard' && git push[/bold white]")

if __name__ == "__main__":
    publish_to_docs()
