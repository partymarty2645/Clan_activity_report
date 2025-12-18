
import re

file_path = "e:/Clan_activity_report/clan_dashboard.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix broken tags (spaces inside tags)
content = re.sub(r'<\s*tr\s*>', '<tr>', content)
content = re.sub(r'<\s*/\s*tr\s*>', '</tr>', content)
content = re.sub(r'<\s*div\s+class="stat-card"\s*>', '<div class="stat-card">', content)
content = re.sub(r'<\s*div\s+class="inactive-tag"\s*>', '<div class="inactive-tag">', content)
content = re.sub(r'\s*</div\s*>', '</div>', content) # Generic closing div fix if needed

# Also fix the weird indentation/newlines if possible, but mainly the valid HTML tags are crucial for the JS to not crash or render garbage.
# The template literals rely on valid HTML strings.

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed clan_dashboard.html")
