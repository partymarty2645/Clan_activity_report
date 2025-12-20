---
description: Deletes .bak files and clears __pycache__ directories to free space.
---
1. Delete .bak files in root
// turbo
2. Remove-Item *.bak -ErrorAction SilentlyContinue
3. Delete __pycache__ directories recursively
// turbo
4. Get-ChildItem -Path . -Recurse -Directory -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch 'node_modules' -and $_.Name -eq '__pycache__' } | Remove-Item -Recurse -Force
