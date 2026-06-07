import os
import re
import sys

# Reconfigure stdout to use utf-8 to handle unicode characters on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
blog_dir = os.path.join(workspace_root, "web-portal", "src", "content", "blog")
img_dir = os.path.join(workspace_root, "web-portal", "public", "images", "news")

def check_orphans():
    md_files = [f for f in os.listdir(blog_dir) if f.endswith(".md")]
    referenced_images = set()
    
    for filename in md_files:
        filepath = os.path.join(blog_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            # Find heroImage: "/images/news/..."
            match = re.search(r'heroImage:\s*["\']/images/news/(.*?)["\']', content)
            if match:
                referenced_images.add(match.group(1))
            else:
                # also try without /images/news/
                match_any = re.search(r'heroImage:\s*["\'](.*?)["\']', content)
                if match_any:
                    img_name = os.path.basename(match_any.group(1))
                    referenced_images.add(img_name)
                    
    all_images = set(os.listdir(img_dir))
    orphaned_images = all_images - referenced_images
    
    print(f"Total active blog posts: {len(md_files)}")
    print(f"Total referenced images: {len(referenced_images)}")
    print(f"Total images in directory: {len(all_images)}")
    print(f"Total orphaned images: {len(orphaned_images)}")
    
    if orphaned_images:
        print("\nOrphaned images list:")
        for idx, img in enumerate(sorted(orphaned_images), 1):
            print(f"{idx}. {img}")
            
if __name__ == "__main__":
    check_orphans()
