import re
from bs4 import BeautifulSoup

file_path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps\1148\content.md"
output_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\current_share_extracted.txt"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    # Strip scripts/styles
    for s in soup(["script", "style"]):
        s.decompose()
        
    text = soup.get_text(separator=' ')
    # Clean up whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned_lines = []
    for line in lines:
        sub_lines = [s.strip() for s in re.split(r'\s{2,}', line) if s.strip()]
        cleaned_lines.extend(sub_lines)
        
    with open(output_path, "w", encoding="utf-8") as out:
        for line in cleaned_lines:
            if len(line) > 15:
                out.write(line + "\n")
                
    print("Done extracting. Lines written:", len(cleaned_lines))

except Exception as e:
    print("Error:", e)
