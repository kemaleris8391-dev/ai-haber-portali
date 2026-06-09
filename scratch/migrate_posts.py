import os
import re

blog_dir = r"web-portal/src/content/blog"
if not os.path.exists(blog_dir):
    print("Blog dizini bulunamadı!")
else:
    files = [f for f in os.listdir(blog_dir) if f.endswith(".md")]
    print(f"Toplam {len(files)} markdown dosyası taranıyor...")
    
    migrated_count = 0
    for f_name in files:
        f_path = os.path.join(blog_dir, f_name)
        with open(f_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        new_content = content
        # Replace category in frontmatter
        new_content = re.sub(r'^category:\s*["\']?otomasyon-plc["\']?\s*$', 'category: "plc"', new_content, flags=re.MULTILINE)
        new_content = re.sub(r'^category:\s*["\']?endustriyel-tamir["\']?\s*$', 'category: "endustriyel-makinalar"', new_content, flags=re.MULTILINE)
        new_content = re.sub(r'^category:\s*["\']?donanim-pratik["\']?\s*$', 'category: "pc"', new_content, flags=re.MULTILINE)
        
        if new_content != content:
            with open(f_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Başarıyla güncellendi: {f_name}")
            migrated_count += 1
            
    print(f"Tamamlandı. Toplam {migrated_count} dosya göç ettirildi.")
