import requests
import os

# Paths
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
image_path = os.path.join(workspace_root, "web-portal", "public", "images", "news", "casper-pad-m10-pro-tanitildi-uretkenlik-ve-egitim-icin-eksik.jpg")
md_path = os.path.join(workspace_root, "web-portal", "src", "content", "blog", "casper-pad-m10-pro-tanitildi-uretkenlik-ve-egitim-icin-eksik.md")

# Pexels photo ID for tablet with keyboard/stylus
photo_url = "https://images.pexels.com/photos/4474033/pexels-photo-4474033.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"

# 1. Download image
print("Görsel indiriliyor...")
r = requests.get(photo_url, timeout=15)
if r.status_code == 200:
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    with open(image_path, "wb") as f:
        f.write(r.content)
    print("Görsel başarıyla indirildi.")

    # 2. Update markdown
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = content.replace('heroImage: "/images/default-news.png"', 'heroImage: "/images/news/casper-pad-m10-pro-tanitildi-uretkenlik-ve-egitim-icin-eksik.jpg"')
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Markdown dosyası başarıyla güncellendi.")
    else:
        print("Hata: Markdown dosyası bulunamadı!")
else:
    print(f"Hata: Görsel indirilemedi. Durum kodu: {r.status_code}")
