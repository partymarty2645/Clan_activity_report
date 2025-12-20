---
description: Deletes .bak files and clears __pycache__ directories to free space.
---
1. Delete .bak files in root
// turbo
2. Remove-Item *.bak -ErrorAction SilentlyContinue
3. Delete __pycache__ directories recursively
// turbo
4. Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
