import re

file_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\fetched_share_response.html"
output_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\gemma_case_matches.txt"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's decode unicode escapes if any
# We'll use a regex to find all \uXXXX and replace them
def decode_escapes(text):
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)

print("Decoding HTML escapes...")
decoded_html = decode_escapes(html)
print("Decoded HTML length:", len(decoded_html))

# Let's search for "gemma" case-insensitively
matches = []
for kw in ["gemma", "yorum", "tıkla", "tikla", "kisisel", "kişisel", "bildirim"]:
    print(f"Searching for '{kw}'...")
    for m in re.finditer(re.escape(kw), decoded_html, re.IGNORECASE):
        start = max(0, m.start() - 250)
        end = min(len(decoded_html), m.end() + 250)
        matches.append((kw, decoded_html[start:end]))

with open(output_path, "w", encoding="utf-8") as out:
    out.write(f"Total matches: {len(matches)}\n\n")
    for idx, (kw, match) in enumerate(matches, 1):
        out.write(f"--- MATCH {idx} (Keyword: {kw}) ---\n")
        out.write(match + "\n")
        out.write("=" * 80 + "\n\n")

print(f"Wrote {len(matches)} matches to gemma_case_matches.txt")
