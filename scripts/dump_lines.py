from pathlib import Path
lines = Path('scripts/mcp_enrich.py').read_text().splitlines()
for i,line in enumerate(lines[:80], start=1):
    print(f"{i:03}: {line}")
