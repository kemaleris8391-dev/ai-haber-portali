import os
import re

path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps\1148\content.md"

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    print("File 1148 content.md exists! Length:", len(content))
    # Look for keywords
    keywords = ["PLC", "Oyun", "Endüstriyel", "makinalar", "pc", "kategori"]
    for kw in keywords:
        count = len(re.findall(kw, content, re.IGNORECASE))
        print(f"Keyword '{kw}': {count} matches")
else:
    print("File 1148 content.md does not exist.")
