import re

file_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\fetched_share_response.html"
output_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\gemma_share_matches.txt"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for "Gemma" and save matches
matches = []
for m in re.finditer(r'Gemma', html):
    start = max(0, m.start() - 250)
    end = min(len(html), m.end() + 250)
    matches.append(html[start:end])

with open(output_path, "w", encoding="utf-8") as out:
    out.write(f"Total matches for 'Gemma': {len(matches)}\n\n")
    for idx, match in enumerate(matches, 1):
        out.write(f"--- MATCH {idx} ---\n")
        out.write(match + "\n")
        out.write("=" * 80 + "\n\n")

print(f"Wrote {len(matches)} matches to gemma_share_matches.txt")
