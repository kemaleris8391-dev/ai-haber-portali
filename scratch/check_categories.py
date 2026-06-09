import os
import re

blog_dir = r"web-portal/src/content/blog"
if not os.path.exists(blog_dir):
    print("Blog directory not found")
else:
    files = [f for f in os.listdir(blog_dir) if f.endswith(".md")]
    categories = {}
    for f_name in files:
        f_path = os.path.join(blog_dir, f_name)
        with open(f_path, "r", encoding="utf-8") as f:
            content = f.read(1000)
        match = re.search(r'^category:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
        if match:
            cat = match.group(1).strip()
            categories.setdefault(cat, []).append(f_name)
        else:
            categories.setdefault("undefined", []).append(f_name)
            
    print("Category Counts:")
    for k, v in categories.items():
        print(f"- {k}: {len(v)} posts")
