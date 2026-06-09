import re
from bs4 import BeautifulSoup

file_path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps\1580\content.md"
output_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\current_share_pure.txt"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Strip markdown prefix
if html.startswith("Title:"):
    html = re.sub(r"^Title:.*?\nDescription:.*?\nSource:.*?\n---\n", "", html, flags=re.DOTALL)

soup = BeautifulSoup(html, 'html.parser')

# Remove scripts, styles, metadata
for tag in soup(["script", "style", "meta", "link", "noscript"]):
    tag.decompose()

# Extract all text elements
elements = soup.find_all(text=True)

lines = []
for el in elements:
    text = el.strip()
    if not text:
        continue
    # Filter out obvious javascript code or JSON templates
    if "window." in text or "function(" in text or "{" in text or "}" in text or "[]" in text:
        continue
    if len(text) > 3:
        lines.append(text)

with open(output_path, "w", encoding="utf-8") as out:
    for line in lines:
        out.write(line + "\n")

print(f"Extracted {len(lines)} clean text blocks.")
