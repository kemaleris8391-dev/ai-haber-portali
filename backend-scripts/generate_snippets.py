import os
import re
import json

blog_dir = 'web-portal/src/content/blog'
output_json = 'backend-scripts/news_snippets.json'

if not os.path.exists(blog_dir):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    blog_dir = os.path.join(base_dir, 'web-portal', 'src', 'content', 'blog')
    output_json = os.path.join(base_dir, 'backend-scripts', 'news_snippets.json')

posts = []

# List all md files
filenames = [f for f in os.listdir(blog_dir) if f.endswith('.md')]

for filename in filenames:
    filepath = os.path.join(blog_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Simple frontmatter parsing
        title_match = re.search(r'^title:\s*(["\'])(.*?)\1\s*$', content, re.MULTILINE)
        if not title_match:
            title_match = re.search(r'^title:\s*(.*?)\s*$', content, re.MULTILINE)
        
        category_match = re.search(r'^category:\s*(["\'])(.*?)\1\s*$', content, re.MULTILINE)
        if not category_match:
            category_match = re.search(r'^category:\s*(.*?)\s*$', content, re.MULTILINE)
            
        title = title_match.group(2) if title_match and len(title_match.groups()) >= 2 else (title_match.group(1) if title_match else "Başlık Yok")
        category = category_match.group(2) if category_match and len(category_match.groups()) >= 2 else (category_match.group(1) if category_match else "Kategori Yok")
        
        title = title.strip('\'"')
        category = category.strip('\'"')
        
        # Extract body (skip frontmatter)
        # Frontmatter is between the first two '---'
        parts = content.split('---')
        body = ""
        if len(parts) >= 3:
            body = '---'.join(parts[2:]) # rejoin if there are other '---' in the text
        else:
            body = content
            
        # Clean markdown syntax (headers, links, bold, etc.) to get clean snippet
        body_clean = re.sub(r'#+\s+', '', body) # remove headers
        body_clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', body_clean) # remove markdown links
        body_clean = re.sub(r'[*_`]', '', body_clean) # remove formatting characters
        body_clean = re.sub(r'\s+', ' ', body_clean).strip() # normalize whitespaces
        
        # Get first 300 characters as snippet
        snippet = body_clean[:300]
        if len(body_clean) > 300:
            snippet += "..."
            
        posts.append({
            'filename': filename,
            'title': title,
            'category': category,
            'snippet': snippet
        })

# Save to snippets file
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(posts, f, ensure_ascii=False, indent=2)

print(f"Başarıyla {len(posts)} haberin başlığı ve snippet'ı {output_json} dosyasına kaydedildi.")
