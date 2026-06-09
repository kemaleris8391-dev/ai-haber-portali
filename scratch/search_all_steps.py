import os
import re

base_dir = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps"
keywords = ["PLC", "Oyun", "Endüstriyel", "kişisel yorum", "Gemma", "telegram"]

matches = []
if os.path.exists(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".md") or file.endswith(".txt"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    for kw in keywords:
                        if kw.lower() in content.lower():
                            # Extract some context
                            pos = content.lower().find(kw.lower())
                            context = content[max(0, pos-100):min(len(content), pos+200)]
                            matches.append((path, kw, context))
                except Exception as e:
                    pass

print(f"Total matches: {len(matches)}")
# Print first 20 matches
for m in matches[:20]:
    print(f"File: {m[0]}")
    print(f"Keyword: {m[1]}")
    print(f"Context: {m[2]}")
    print("-" * 50)
