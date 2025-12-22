---
description: Run full system maintenance (Optimize DB, Rotate Logs, Clean Backups)
---
1. Optimize Database
// turbo
python scripts/optimize_database.py

2. Clear .bak files
// turbo
Remove-Item *.bak -ErrorAction SilentlyContinue

3. Clear pycache
// turbo
Get-ChildItem -Path . -Recurse -Directory -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch 'node_modules' -and $_.Name -eq '__pycache__' } | Remove-Item -Recurse -Force

4. Archive Logs
// turbo
Move-Item app.log backups/app_$(Get-Date -Format "yyyyMMdd_HHmmss").log -ErrorAction SilentlyContinue

5. Archive Backups
// turbo
Move-Item *.bak backups/ -ErrorAction SilentlyContinue
Move-Item*_backup.xlsx backups/ -ErrorAction SilentlyContinue
