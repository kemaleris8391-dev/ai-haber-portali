import os
import re
import sys
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

# Windows CP1254 terminal emoji encoding fix
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def check_links():
    dist_dir = os.path.abspath("../web-portal/dist")
    if not os.path.exists(dist_dir):
        print(f"Hata: dist dizini bulunamadi: {dist_dir}")
        return

    html_files = []
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            if file.endswith(".html") or file.endswith(".xml"):
                html_files.append(os.path.join(root, file))

    print(f"Toplam {len(html_files)} dosya taraniyor...")

    broken_links = []
    total_links_checked = 0

    # Local paths normalization
    def is_local_file_exists(path):
        # Remove query parameters/hashes
        path = path.split("?")[0].split("#")[0]
        if not path:
            return True
            
        # Decode URL-encoded characters (like %E2%80%99)
        path = unquote(path)

        # Normalize relative path
        if path.startswith("/"):
            target_path = os.path.join(dist_dir, path.lstrip("/"))
        else:
            return True # skip relative links like href="#" or external
            
        # If it points to a directory, check if index.html exists in that dir
        if os.path.isdir(target_path):
            return os.path.exists(os.path.join(target_path, "index.html"))
        
        # Check direct file existence (like /favicon.ico or /images/...)
        if os.path.exists(target_path):
            return True
            
        # Check if folder index exists (Astro clean URLs: /blog/slug -> /blog/slug/index.html)
        if not os.path.exists(target_path):
            alt_path = target_path.rstrip("/") + "/index.html"
            if os.path.exists(alt_path):
                return True
            # Check if it is a directory target without index
            alt_dir = target_path.rstrip("/")
            if os.path.isdir(alt_dir) and os.path.exists(os.path.join(alt_dir, "index.html")):
                return True
                
        return False

    for file_path in html_files:
        rel_file_path = os.path.relpath(file_path, dist_dir)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Dosya okunamadi: {rel_file_path} - {e}")
            continue

        soup = BeautifulSoup(content, "html.parser")
        
        # Find all links
        links = []
        for tag in soup.find_all(["a", "link"]):
            href = tag.get("href")
            if href:
                links.append(("href", href))
                
        for tag in soup.find_all(["img", "script"]):
            src = tag.get("src")
            if src:
                links.append(("src", src))

        for attr, link in links:
            # Skip external links
            parsed = urlparse(link)
            is_external = bool(parsed.netloc) and not parsed.netloc.endswith("aihaberler.web.app") and not parsed.netloc.endswith("ai-haber-portali.vercel.app")
            
            if is_external:
                continue
                
            # Internal links validation
            local_path = parsed.path
            if not local_path and not parsed.netloc:
                # anchor links like href="#content"
                continue
                
            total_links_checked += 1
            if not is_local_file_exists(local_path):
                broken_links.append({
                    "file": rel_file_path,
                    "attr": attr,
                    "link": link,
                    "resolved_path": local_path
                })

    print(f"\nTarama Tamamlandi. Toplam Kontrol Edilen Yerel Link: {total_links_checked}")
    if broken_links:
        print(f"❌ Toplam {len(broken_links)} adet KIRIK LİNK bulundu:")
        # Group by file for readability
        grouped = {}
        for item in broken_links:
            grouped.setdefault(item["file"], []).append(f"  - [{item['attr']}] {item['link']}")
            
        for file, items in grouped.items():
            print(f"\nDosya: {file}")
            for item in items:
                print(item)
    else:
        print("✅ Harika! Hicbir kirik yerel link bulunamadi.")

if __name__ == "__main__":
    check_links()
