import re

file_path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\d2701d74-9c8c-4d30-8106-07fa27330cb4\.system_generated\steps\5\content.md"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Find all strings in the json format or script tags that have length > 50
    # Gemini shares often encode the conversation in a JSON array inside <script nonce="...">AF_initDataCallback(...)</script>
    # We can just extract all strings starting with a letter that have space in them and no HTML tags.
    
    # regex for grabbing potential turkish/english text
    # Let's just strip all html tags and print
    from html.parser import HTMLParser

    class HTMLFilter(HTMLParser):
        text = ""
        def handle_data(self, data):
            self.text += data + "\n"

    f = HTMLFilter()
    f.feed(html)
    
    # also try extracting text from script tags, since the data is usually in JS.
    # WIZ_global_data and AF_initDataCallback
    import json
    
    # Try finding arrays like [[["text", ...
    matches = re.findall(r'\[\[\["(.*?)"', html)
    
    with open(r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\extracted.txt", "w", encoding="utf-8") as out:
        out.write("--- HTML TEXT ---\n")
        out.write(f.text)
        out.write("\n\n--- REGEX MATCHES ---\n")
        for m in matches:
            out.write(m + "\n")
            
    print("Done extracting. Check scratch/extracted.txt")
except Exception as e:
    print(e)
