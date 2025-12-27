---
description: Perform a clean rebuild of the database (Wipe + Deep Harvest)
---

This workflow completely resets the database and repopulates it with fresh history.

1. **Warning**: This process deletes `clan_data.db` and takes significant time (1-2 hours) to fetch Discord history.
2. **Backup**: An automatic backup is created in `backups/` before deletion.

# Steps

1. Run the rebuild script:

   ```powershell
   python scripts/rebuild_database.py
   ```

   (Add `--force` to skip confirmation)

2. Monitors progress via standard output.

3. Automatically runs Report and Export phases upon completion.
