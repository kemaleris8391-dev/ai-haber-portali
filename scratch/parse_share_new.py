import re
import json
from bs4 import BeautifulSoup

file_path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps\1580\content.md"
output_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\current_share_extracted.txt"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Find the JSON data inside the script tags or global data
    # Gemini share pages usually contain a script with window.WIZ_global_data or similar JSON arrays.
    # Let's extract all script tags.
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all("script")
    
    text_content = []
    
    # Also extract regular page text
    body_text = soup.get_text(separator="\n")
    for line in body_text.split("\n"):
        line = line.strip()
        if len(line) > 10:
            text_content.append(line)
            
    # Try finding large string payloads inside scripts
    for script in scripts:
        if script.string:
            # Look for JSON arrays or large blocks
            matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', script.string)
            for m in matches:
                # Clean unicode escapes
                try:
                    decoded = m.encode().decode('unicode-escape')
                    if any(c in decoded for c in ["ı", "ş", "ğ", "ö", "ç", "ü", "I", "Ş", "Ğ", "Ö", "Ç", "Ü"]) and len(decoded) > 15:
                        text_content.append(decoded.strip())
                except:
                    if len(m) > 30 and any(c in m for c in ["ı", "ş", "ğ", "ö", "ç", "ü"]):
                        text_content.append(m.strip())

    # Write unique lines
    unique_lines = []
    seen = set()
    for line in text_content:
        line_clean = re.sub(r'\s+', ' ', line).strip()
        if line_clean and line_clean not in seen and len(line_clean) > 10:
            seen.add(line_clean)
            unique_lines.append(line_clean)
            
    with open(output_path, "w", encoding="utf-8") as out:
        for line in unique_lines:
            out.write(line + "\n\n")
            
    print("Done extracting. Unique lines written:", len(unique_lines))

except Exception as e:
    print("Error:", e)
