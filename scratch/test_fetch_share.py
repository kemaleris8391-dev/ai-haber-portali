import requests
import re
import json

url = "https://gemini.google.com/share/cdc3846d4147"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

print("Fetching URL...")
r = requests.get(url, headers=headers)
print("Status:", r.status_code)

html = r.text
print("Length of HTML:", len(html))

# Let's search if "PLC" or "Oyun" or "makinalar" or "kategori" exists anywhere in the html
for kw in ["PLC", "Oyun", "makina", "PC", "Endüstriyel", "kategori"]:
    count = len(re.findall(kw, html, re.IGNORECASE))
    print(f"Keyword '{kw}': {count} matches")

# Save to a scratch file
with open("fetched_share_response.html", "w", encoding="utf-8") as f:
    f.write(html)
