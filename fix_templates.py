
import re
from pathlib import Path

path = Path(r"e:\Clan_activity_report\clan_dashboard.html")
content = path.read_text(encoding="utf-8")

# Fix 1: Join split template literals "$ {" -> "${"
# Handles newlines and spaces between $ and {
new_content = re.sub(r'\$\s+\{', '${', content)

# Fix 2: Clean up multi-line template expressions that might have been split weirdly
# e.g. ${
#      variable
#    }
# We can try to compact them, but simply fixing the start token is the most critical.
# Let's also look for "$ {" which might be on one line.
new_content = re.sub(r'\$\s*\{', '${', new_content)

path.write_text(new_content, encoding="utf-8")
print(f"Fixed template literals in {path}")
