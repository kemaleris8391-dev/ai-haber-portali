import re
from bs4 import BeautifulSoup

def parse_html_file(file_path, output_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip markdown headers if any
    if content.startswith("Title:"):
        content = re.sub(r"^Title:.*?\nDescription:.*?\nSource:.*?\n---\n", "", content, flags=re.DOTALL)
        
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find the main article content
    # In google help centers, the article is usually inside <article> or class "cc"
    article = soup.find('article') or soup.find(class_='cc')
    if not article:
        article = soup
        
    # Get clean text
    text = ""
    for elem in article.find_all(['h1', 'h2', 'h3', 'p', 'li']):
        text += elem.get_text().strip() + "\n"
        if elem.name.startswith('h'):
            text += "=" * len(elem.get_text().strip()) + "\n"
            
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Cleaned text written to {output_path}")

if __name__ == "__main__":
    parse_html_file(
        r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps\65\content.md",
        r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\adsense_reqs_clean.txt"
    )
    parse_html_file(
        r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps\69\content.md",
        r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\thin_content_clean.txt"
    )
