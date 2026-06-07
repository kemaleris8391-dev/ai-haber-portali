"""
Mevcut tüm .jpg haber görsellerini WebP formatına dönüştürür ve
ilgili .md dosyalarındaki heroImage referanslarını günceller.
"""
import os
import glob
from PIL import Image

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "web-portal", "public", "images", "news")
CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "web-portal", "src", "content", "blog")

def convert_to_webp(input_path, output_path, max_width=1200, quality=82):
    """JPG/PNG -> Optimized WebP"""
    try:
        img = Image.open(input_path)
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (18, 18, 18))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        w, h = img.size
        if w > max_width:
            ratio = max_width / w
            new_h = int(h * ratio)
            img = img.resize((max_width, new_h), Image.LANCZOS)
        
        img.save(output_path, "WEBP", quality=quality, method=4)
        return True
    except Exception as e:
        print(f"  HATA: {e}")
        return False

def main():
    images_dir = os.path.abspath(IMAGES_DIR)
    content_dir = os.path.abspath(CONTENT_DIR)
    
    jpg_files = glob.glob(os.path.join(images_dir, "*.jpg"))
    print(f"Toplam {len(jpg_files)} adet JPG dosyası bulundu.\n")
    
    converted = 0
    total_original_kb = 0
    total_webp_kb = 0
    
    for jpg_path in jpg_files:
        basename = os.path.basename(jpg_path)
        name_without_ext = os.path.splitext(basename)[0]
        webp_path = os.path.join(images_dir, f"{name_without_ext}.webp")
        
        original_size = os.path.getsize(jpg_path) / 1024
        
        if convert_to_webp(jpg_path, webp_path):
            webp_size = os.path.getsize(webp_path) / 1024
            savings = ((original_size - webp_size) / original_size * 100) if original_size > 0 else 0
            print(f"[OK] {basename} -> .webp  ({original_size:.0f}KB -> {webp_size:.0f}KB, -%{savings:.0f})")
            
            total_original_kb += original_size
            total_webp_kb += webp_size
            converted += 1
            
            # Eski JPG dosyasını sil
            os.remove(jpg_path)
        else:
            print(f"[FAIL] {basename} dönüştürülemedi, atlanıyor.")
    
    # Markdown dosyalarındaki heroImage referanslarını güncelle (.jpg -> .webp)
    md_files = glob.glob(os.path.join(content_dir, "*.md"))
    md_updated = 0
    for md_path in md_files:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if '.jpg"' in content or ".jpg'" in content:
            new_content = content.replace('.jpg"', '.webp"').replace(".jpg'", ".webp'")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            md_updated += 1
    
    print(f"\n{'='*60}")
    print(f"SONUÇ:")
    print(f"  Dönüştürülen görsel  : {converted} / {len(jpg_files)}")
    print(f"  Güncellenen .md dosya: {md_updated}")
    print(f"  Toplam Orijinal      : {total_original_kb/1024:.1f} MB")
    print(f"  Toplam WebP          : {total_webp_kb/1024:.1f} MB")
    if total_original_kb > 0:
        total_savings = ((total_original_kb - total_webp_kb) / total_original_kb * 100)
        print(f"  Toplam Tasarruf      : -%{total_savings:.0f} ({(total_original_kb - total_webp_kb)/1024:.1f} MB kazanıldı)")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
