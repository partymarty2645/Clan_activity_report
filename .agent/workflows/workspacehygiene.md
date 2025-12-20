---
description: Cleans up temporary files, rotates logs, and organizes loose files.
---
1. Rotate app.log to backups folder
// turbo
2. Move-Item app.log backups/app_$(Get-Date -Format "yyyyMMdd_HHmmss").log -ErrorAction SilentlyContinue
3. Move loose .bak files to backups
// turbo
4. Move-Item *.bak backups/ -ErrorAction SilentlyContinue
5. Archive text reports
// turbo
6. Move-Item purge_list.txt, moderation_report.txt, officer_audit.txt, weekly_spotlight.txt reports/archive/ -ErrorAction SilentlyContinue
7. Move Excel backups
// turbo
8. Move-Item *_backup.xlsx backups/ -ErrorAction SilentlyContinue
