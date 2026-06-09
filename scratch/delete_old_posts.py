import os
import re

base_dir = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali"
blog_dir = os.path.join(base_dir, "web-portal", "src", "content", "blog")
images_dir = os.path.join(base_dir, "web-portal", "public", "images", "news")

NEW_CATEGORIES = {"otomasyon-plc", "endustriyel-tamir", "donanim-pratik"}

deleted_posts = 0
deleted_images = 0

if not os.path.exists(blog_dir):
    print("Blog directory not found!")
    exit(1)

for f_name in os.listdir(blog_dir):
    if not f_name.endswith(".md"):
        continue
    f_path = os.path.join(blog_dir, f_name)
    try:
        with open(f_path, "r", encoding="utf-8") as f:
            content = f.read(1000)
            
        category_match = re.search(r'^category:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
        image_match = re.search(r'^heroImage:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
        
        category = category_match.group(1).strip().lower() if category_match else ""
        
        # If the category is old, delete the file and image
        if category not in NEW_CATEGORIES:
            print(f"Deleting old post: {f_name} (Category: {category})")
            
            # 1. Delete image
            if image_match:
                img_path = image_match.group(1).strip()
                # e.g., /images/news/some-slug.webp -> some-slug.webp
                img_name = os.path.basename(img_path)
                full_img_path = os.path.join(images_dir, img_name)
                if os.path.exists(full_img_path):
                    os.remove(full_img_path)
                    deleted_images += 1
                    
            # 2. Delete markdown
            os.remove(f_path)
            deleted_posts += 1
            
    except Exception as e:
        print(f"Error processing {f_name}: {e}")

print(f"Cleanup completed! Deleted {deleted_posts} posts and {deleted_images} images.")
