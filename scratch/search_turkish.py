import re
import json

file_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\extracted.txt"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# find all strings in quotes
strings = re.findall(r'"((?:[^"\\]|\\.)*)"', text)

turkish_words = [" ve ", " bir ", " bu ", " için ", " ile ", " da ", " de "]

found = []
for s in strings:
    s = s.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
    try:
        s = s.encode('utf-8').decode('unicode_escape')
    except:
        pass
        
    if len(s) > 100:
        s_lower = s.lower()
        if any(w in s_lower for w in turkish_words):
            found.append(s)

with open(r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\turkish_text.txt", "w", encoding="utf-8") as out:
    for f in set(found):
        out.write("--- BLOCK ---\n")
        out.write(f + "\n\n")

print(f"Found {len(set(found))} blocks.")
