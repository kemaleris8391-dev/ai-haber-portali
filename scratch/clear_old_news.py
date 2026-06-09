import os
import glob
import json

# Temizlik scripti dosyasının bulunduğu yerin bir üst dizinini proje kök dizini kabul edelim
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

blog_dir = os.path.join(base_dir, 'web-portal', 'src', 'content', 'blog')
images_dir = os.path.join(base_dir, 'web-portal', 'public', 'images', 'news')
news_db_path = os.path.join(base_dir, 'backend-scripts', 'news_db.json')
news_snippets_path = os.path.join(base_dir, 'backend-scripts', 'news_snippets.json')

print("Portal sıfırlama işlemi başlatılıyor...")

# 1. Blog markdown dosyalarını sil
deleted_md = 0
if os.path.exists(blog_dir):
    md_files = glob.glob(os.path.join(blog_dir, "*.md"))
    for f in md_files:
        try:
            os.remove(f)
            deleted_md += 1
        except Exception as e:
            print(f"Hata - Markdown silinemedi {f}: {e}")
else:
    print(f"Uyarı - Blog dizini bulunamadı: {blog_dir}")
print(f"SİLİNDİ: {deleted_md} adet Markdown dosyası.")

# 2. Resimleri sil
deleted_img = 0
if os.path.exists(images_dir):
    img_files = glob.glob(os.path.join(images_dir, "*"))
    for f in img_files:
        # Alt dizinleri değil sadece dosyaları sil
        if os.path.isfile(f):
            try:
                os.remove(f)
                deleted_img += 1
            except Exception as e:
                print(f"Hata - Resim silinemedi {f}: {e}")
else:
    print(f"Uyarı - Görsel dizini bulunamadı: {images_dir}")
print(f"SİLİNDİ: {deleted_img} adet Görsel dosyası.")

# 3. news_db.json sıfırla
try:
    with open(news_db_path, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    print("SIFIRLANDI: news_db.json veritabanı boşaltıldı.")
except Exception as e:
    print(f"Hata - news_db.json sıfırlanamadı: {e}")

# 4. news_snippets.json sıfırla
try:
    with open(news_snippets_path, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    print("SIFIRLANDI: news_snippets.json veritabanı boşaltıldı.")
except Exception as e:
    print(f"Hata - news_snippets.json sıfırlanamadı: {e}")

print("Tebrikler, tüm eski veriler başarıyla temizlendi!")
