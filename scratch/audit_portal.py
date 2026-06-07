import os
import hashlib

# Paths
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
blog_dir = os.path.join(workspace_root, "web-portal", "src", "content", "blog")
public_dir = os.path.join(workspace_root, "web-portal", "public")

def get_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def run_audit():
    print("--- PORTAL AUDIT BAŞLATILDI ---")
    
    # 1. Scan blog markdown files
    md_files = [f for f in os.listdir(blog_dir) if f.endswith(".md")]
    print(f"Toplam Haber Sayısı: {len(md_files)}")
    
    missing_images = []
    default_news_images = []
    image_paths_in_posts = {}
    
    for filename in md_files:
        filepath = os.path.join(blog_dir, filename)
        hero_image = None
        title = ""
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("heroImage:"):
                    hero_image = line.split(":", 1)[1].strip().strip('"').strip("'")
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"').strip("'")
        
        if not hero_image:
            print(f"UYARI: '{filename}' için heroImage tanımlanmamış!")
            continue
            
        image_paths_in_posts[filename] = {
            "title": title,
            "hero_image": hero_image
        }
        
        # Check if it uses default news
        if "default-news.png" in hero_image:
            default_news_images.append((filename, title))
            
        # Check if the image physically exists
        if hero_image.startswith("/"):
            # absolute path in public
            img_physical_path = os.path.join(public_dir, hero_image.lstrip("/"))
            if not os.path.exists(img_physical_path):
                missing_images.append((filename, title, hero_image))
        else:
            print(f"UYARI: '{filename}' içindeki görsel yolu formatı yanlış: {hero_image}")

    print("\n--- 1. GÖRSEL VARLIĞI VE VARSAYILAN KONTROLÜ ---")
    print(f"Varsayılan görsel kullanan haber sayısı: {len(default_news_images)}")
    for f, t in default_news_images:
        print(f"  - Dosya: {f} | Başlık: {t}")
        
    print(f"Fiziksel olarak bulunamayan (Broken) görsel sayısı: {len(missing_images)}")
    for f, t, img in missing_images:
        print(f"  - Dosya: {f} | Başlık: {t} | Görsel: {img}")

    # 2. Check for duplicate image contents
    print("\n--- 2. YENİ MÜKERRER (DUPLICATE) BİNARY GÖRSEL KONTROLÜ ---")
    images_dir = os.path.join(public_dir, "images", "news")
    img_files = [f for f in os.listdir(images_dir) if f.endswith((".jpg", ".jpeg", ".png", ".webp"))]
    
    hash_map = {}
    for filename in img_files:
        filepath = os.path.join(images_dir, filename)
        try:
            h = get_md5(filepath)
            if h not in hash_map:
                hash_map[h] = []
            hash_map[h].append(filename)
        except Exception as e:
            print(f"Hata: '{filename}' hash alınamadı. {e}")
            
    duplicate_groups = {h: files for h, files in hash_map.items() if len(files) > 1}
    print(f"Mükerrer içerikli görsel grup sayısı: {len(duplicate_groups)}")
    
    total_duplicate_files = 0
    for h, files in duplicate_groups.items():
        print(f"  - Hash: {h} | Dosyalar ({len(files)} adet):")
        for f in files:
            print(f"    * {f}")
        total_duplicate_files += (len(files) - 1)
        
    print(f"\nToplam giderilmesi gereken kopya görsel (over-use) dosyası: {total_duplicate_files}")
    print("--- PORTAL AUDIT BİTTİ ---")

if __name__ == "__main__":
    run_audit()
