import os
import re

blog_dir = 'web-portal/src/content/blog'
output_file = 'backend-scripts/tum_haber_basliklari.md'

if not os.path.exists(blog_dir):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    blog_dir = os.path.join(base_dir, 'web-portal', 'src', 'content', 'blog')
    output_file = os.path.join(base_dir, 'backend-scripts', 'tum_haber_basliklari.md')

posts = []

for filename in os.listdir(blog_dir):
    if filename.endswith('.md'):
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
            
            # Clean title quotes if any
            title = title.strip('\'"')
            category = category.strip('\'"')
            
            posts.append({
                'filename': filename,
                'title': title,
                'category': category
            })

# Sort by category and title
posts.sort(key=lambda x: (x['category'], x['title']))

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("# Tüm Haber Başlıkları ve Kategorileri\n\n")
    f.write(f"Toplam Haber Sayısı: {len(posts)}\n\n")
    f.write("| No | Kategori | Başlık | Dosya Adı |\n")
    f.write("|---|---|---|---|\n")
    for i, post in enumerate(posts, 1):
        f.write(f"| {i} | {post['category']} | {post['title']} | `{post['filename']}` |\n")

print(f"Başarıyla {len(posts)} haber listelendi ve {output_file} dosyasına yazıldı.")
