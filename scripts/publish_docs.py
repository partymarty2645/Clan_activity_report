
import os
import shutil
import sys
from datetime import datetime
from rich.console import Console

console = Console()

def check_dashboard_fixes_applied():
    """Check if dashboard fixes have been manually applied and should be preserved."""
    dashboard_fixes_file = "DASHBOARD_FIXES_APPLIED.md"
    docs_dashboard = "docs/dashboard_logic.js"
    
    # If fixes documentation exists and docs files are newer than root files,
    # assume manual fixes are in place
    if os.path.exists(dashboard_fixes_file) and os.path.exists(docs_dashboard):
        root_dashboard = "dashboard_logic.js"
        if os.path.exists(root_dashboard):
            docs_time = os.path.getmtime(docs_dashboard)
            root_time = os.path.getmtime(root_dashboard)
            
            # If docs version is newer, preserve it
            if docs_time > root_time:
                return True
    
    return False

def publish_to_docs():
    console.print("[bold cyan]🚀 Starting GitHub Pages Deployment (Publish to /docs)...[/bold cyan]")
    
    root_dir = os.getcwd()
    docs_dir = os.path.join(root_dir, "docs")
    
    # Check if manual dashboard fixes should be preserved
    preserve_fixes = check_dashboard_fixes_applied()
    if preserve_fixes:
        console.print("[bold yellow]⚠️  Manual dashboard fixes detected - preserving existing files[/bold yellow]")
        console.print("[yellow]   Files in /docs/ are newer than root files, skipping dashboard overwrite[/yellow]")
        console.print("[yellow]   Only updating data files (clan_data.js, ai_data.js)[/yellow]")
    
    # 1. Ensure docs directory exists
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        console.print(f"[green]Created directory: {docs_dir}[/green]")
    
    # 2. Clean docs directory (Safety: Only delete specific known files/folders to avoid blowing up .git if someone initialized there)
    # Actually, standard practice is to wipe it or overwrite. Let's overwrite.
    # Warning: If docs/CNAME exists, keep it.
    
    # List of files/folders to copy
    if preserve_fixes:
        # Only copy data files when preserving dashboard fixes
        files_to_copy = {
            "clan_data.js": "clan_data.js", # Data file (always update)
            "ai_data.js": "ai_data.js",   # AI Data file (always update)
            "clan_data.json": "clan_data.json", # Raw JSON (always update)
        }
        console.print("[yellow]   Updating data files only, preserving dashboard logic[/yellow]")
    else:
        # Normal full deployment
        files_to_copy = {
            "clan_dashboard.html": "index.html", # RENAME to index.html
            "dashboard_logic.js": "dashboard_logic.js",
            "clan_data.js": "clan_data.js", # Data file
            "ai_data.js": "ai_data.js",   # AI Data file
            "clan_data.json": "clan_data.json", # Raw JSON (if needed by JS)
        }
    
    dirs_to_copy = ["assets"] if not preserve_fixes else []
    
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
    if preserve_fixes:
        console.print("[bold green]✅ Data files updated successfully! Dashboard fixes preserved.[/bold green]")
        console.print("[green]   Your manual dashboard improvements are still active[/green]")
    else:
        console.print("[bold green]✨ Deployment Ready![/bold green]")
    
    console.print("To go live: [bold white]git add docs && git commit -m 'Deploy Dashboard' && git push[/bold white]")

if __name__ == "__main__":
    publish_to_docs()
