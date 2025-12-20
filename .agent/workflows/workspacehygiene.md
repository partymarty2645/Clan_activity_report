---
description: Cleans up temporary files, rotates logs, and organizes loose files.
---
1. Rotate app.log to backups folder
// turbo
2. Move-Item app.log backups/app_$(Get-Date -Format "yyyyMMdd_HHmmss").log -ErrorAction SilentlyContinue
3. Move loose .bak files to backups
// turbo
4. Move-Item *.bak backups/ -ErrorAction SilentlyContinue
