import json
import os
import feedparser
from bs4 import BeautifulSoup
import sys
import re
from datetime import datetime, timezone, timedelta
TR_TZ = timezone(timedelta(hours=3))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Windows CP1254 terminal emoji encoding fix
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

import firebase_helper

def clean_html(html_content):
    """HTML etiketlerini temizler ve düz metin döndürür."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()

def load_config(config_path="config.json"):
    """Konfigürasyon dosyasını yükler."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config dosyası bulunamadı: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_db(db_path):
    """Daha önce işlenmiş haberleri tutan basit JSON veritabanını yükler."""
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_db(db_path, db_data):
    """Veritabanını kaydeder."""
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

def get_existing_titles(limit=40, hours_back=30):
    """Astro blog klasöründeki haberlerin başlıklarını çeker.
    hours_back belirtilmişse, son X saatte yayınlanmış haberlerin başlıklarını döndürür.
    Değilse son 'limit' adet haberi döndürür.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    blog_dir = os.path.abspath(os.path.join(base_dir, "../web-portal/src/content/blog"))
    
    if not os.path.exists(blog_dir):
        return []
        
    md_files = [f for f in os.listdir(blog_dir) if f.endswith(".md")]
    
    # Türkiye saat dilimine göre eşik zamanı hesapla
    now_tr = datetime.now(TR_TZ)
    threshold_time = now_tr - timedelta(hours=hours_back) if hours_back is not None else None
    
    parsed_posts = []
    for file in md_files:
        file_path = os.path.join(blog_dir, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(1000) # Read only frontmatter
                
            pub_match = re.search(r'^pubDate:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
            title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
            
            if pub_match and title_match:
                pub_val = pub_match.group(1).strip()
                title = title_match.group(1).strip()
                
                # pubDate tarihini parse et
                try:
                    dt_post = datetime.fromisoformat(pub_val[:19])
                    if dt_post.tzinfo is None:
                        dt_post = dt_post.replace(tzinfo=TR_TZ)
                except Exception:
                    continue
                
                # Belirlenen saat diliminin dışındaysa atla
                if threshold_time is not None:
                    if dt_post < threshold_time:
                        continue
                
                parsed_posts.append((pub_val, title))
        except Exception as e:
            print(f"BİLGİ: {file} okunamadı veya ayrıştırılamadı: {e}")
            
    # Sort posts by pubDate descending (latest first)
    parsed_posts.sort(key=lambda x: x[0], reverse=True)
    
    if hours_back is not None:
        titles = [post[1] for post in parsed_posts]
        print(f"Son {hours_back} saatteki haber başlığı sayısı: {len(titles)}")
        return titles
    
    # Eski mod: son N haberi döndür
    latest_titles = [post[1] for post in parsed_posts[:limit]]
    return latest_titles

def is_similar_to_existing(new_title, existing_titles, word_threshold=0.30, char_threshold=0.38):
    """Yeni başlığın mevcut başlıklarla olan Jaccard benzerliğini hem kelime hem de karakter N-Gram düzeyinde denetler."""
    import re
    
    def clean_text(text):
        """Metni küçük harfe çevirir, Türkçe çekim eklerini kesme işaretiyle temizler ve noktalama işaretlerini siler."""
        text = text.lower()
        # Türkçe kesme işareti ve sonrasındaki eki temizle (örn: apple'ın -> apple, acer'dan -> acer)
        text = re.sub(r"'[a-z0-9ıışşğğççööüü]*", "", text)
        tr_map = str.maketrans("çğıöşü", "cgiosu")
        text = text.translate(tr_map)
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def tokenize_words(text):
        """Temiz metinden bağlaçları/stop-wordleri ayıklayarak kelime kümesi döndürür."""
        cleaned = clean_text(text)
        words = set(cleaned.split())
        stop_words = {
            "ve", "veya", "bir", "ile", "de", "da", "icin", "en", "bu", "o", "ise", "ki", 
            "yeni", "dev", "hakkinda", "neler", "nelerdir", "mi", "mu", "milyon", "milyar", 
            "kisi", "adet", "son", "ilk", "a", "an", "the", "of", "and", "in", "on", "at", "for"
        }
        return words - stop_words

    def get_char_ngrams(text, n_list=[3, 4]):
        """Temizlenmiş metinden (boşluksuz) belirtilen N değerlerinde karakter n-gram kümeleri çıkarır."""
        cleaned = "".join(clean_text(text).split())
        ngrams = set()
        for n in n_list:
            if len(cleaned) >= n:
                for i in range(len(cleaned) - n + 1):
                    ngrams.add(cleaned[i:i+n])
        return ngrams

    words_new = tokenize_words(new_title)
    chars_new = get_char_ngrams(new_title)
    
    if not words_new:
        return False
        
    for ext_title in existing_titles:
        # 1. Kelime Düzeyinde Jaccard Benzerliği
        words_ext = tokenize_words(ext_title)
        word_sim = 0.0
        if words_ext:
            intersection_w = words_new.intersection(words_ext)
            union_w = words_new.union(words_ext)
            word_sim = len(intersection_w) / len(union_w)
            
        # 2. Karakter N-Gram Düzeyinde Jaccard Benzerliği (Türkçe Eklerine Karşı Koruma)
        chars_ext = get_char_ngrams(ext_title)
        char_sim = 0.0
        if chars_ext:
            intersection_c = chars_new.intersection(chars_ext)
            union_c = chars_new.union(chars_ext)
            char_sim = len(intersection_c) / len(union_c)
            
        # Eğer herhangi bir benzerlik eşiği aşılırsa mükerrer kabul et
        if word_sim >= word_threshold:
            print(f"Benzerlik Engeli (Kelime): '{new_title}' başlığı, mevcut '{ext_title}' ile benzer (Oran: {word_sim:.2f})")
            return True
            
        if char_sim >= char_threshold:
            print(f"Benzerlik Engeli (N-Gram): '{new_title}' başlığı, mevcut '{ext_title}' ile benzer (Oran: {char_sim:.2f})")
            return True
            
    return False

def fetch_new_news():
    """RSS beslemelerinden yeni haberleri çekip döndürür.
    3 Katmanlı Filtreleme:
      Katman 1: Link bazlı kalıcı kara liste (Firestore) → Sıfır maliyet
      Katman 2: Yerel Jaccard + N-Gram benzerlik (bugün+dün) → Sıfır API maliyeti
      Katman 3: Gemma 31B batch semantik doğrulama → Minimum API maliyeti
    """
    config = load_config()
    db_path = config["settings"]["db_path"]
    max_per_source = config["settings"]["max_news_per_source_run"]
    
    processed_links = load_db(db_path)
    
    # Katman 1: Firestore kara listesini yükle (tek read)
    blacklisted_links = firebase_helper.get_blacklisted_links()
    
    # Onay bekleyen ve silme kuyruğundaki haberleri Firestore'dan yükle
    try:
        pending_titles, pending_urls = firebase_helper.get_pending_posts_info()
    except Exception as e:
        print(f"UYARI: Onay bekleyen haber bilgileri alınamadı: {e}")
        pending_titles, pending_urls = [], set()
        
    # Onay bekleyen linkleri de atlanacak linkler listesine ekle
    if pending_urls:
        blacklisted_links = blacklisted_links.union(pending_urls)
    
    # Katman 2 için: Geriye dönük son 30 saatlik haber başlıklarını al
    existing_titles = get_existing_titles(hours_back=30)
    
    # Onay bekleyen başlıkları da benzerlik ve mükerrerlik kontrolleri için mevcut başlıklar listesine ekle
    if pending_titles:
        existing_titles.extend(pending_titles)
        
    new_news_list = []
    newly_blacklisted = []  # Bu çalışmada elenen linkler (toplu kara liste yazımı için)
    blacklist_skipped = 0   # Kara liste sayesinde atlanan haber sayısı
    jaccard_skipped = 0     # Jaccard benzerlik ile elenen haber sayısı
    
    # RSS kaynaklarını Firestore'dan dinamik olarak çek
    sources = firebase_helper.get_rss_sources()
    
    print("RSS beslemeleri taranıyor...")
    for source in sources:
        name = source["name"]
        url = source["url"]
        category = source["category"]
        
        print(f"Kaynak taranıyor: {name} ({url})")
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.text)
        except Exception as e:
            print(f"Hata: {name} kaynağından veri çekilemedi. Detay: {e}")
            continue
            
        source_count = 0
        for entry in feed.entries:
            if source_count >= max_per_source:
                break
                
            link = getattr(entry, "link", "")
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            published = getattr(entry, "published", "")
            
            if not link:
                continue
            
            # ═══ KATMAN 1: Kalıcı Kara Liste Kontrolü (Sıfır Maliyet) ═══
            if link in blacklisted_links:
                blacklist_skipped += 1
                continue
            
            # Daha önce işlendiyse atla
            if link in processed_links:
                continue
                
            # ═══ KATMAN 2: Yerel Jaccard + N-Gram Benzerlik (Bugün+Dün) ═══
            if is_similar_to_existing(title, existing_titles):
                newly_blacklisted.append(link)  # Elenen linki kara listeye ekle
                jaccard_skipped += 1
                continue
                
            # CRITICAL STATE BUG FIX: Kabul edilen başlığı anında mevcut listeye ekle ki 
            # aynı çalışmadaki benzer diğer haberler de elenebilsin!
            existing_titles.append(title)
                
            clean_summary = clean_html(summary)
            
            new_news_list.append({
                "source": name,
                "category": category,
                "title": title,
                "link": link,
                "summary": clean_summary,
                "published": published
            })
            
            # Veritabanına ekle
            processed_links.append(link)
            source_count += 1
    
    # Katman 1-2 raporu
    if blacklist_skipped > 0:
        print(f"\n🛡️ Katman 1 (Kara Liste): {blacklist_skipped} adet haber kara listeden dolayı sessizce atlandı.")
    if jaccard_skipped > 0:
        print(f"🔍 Katman 2 (Jaccard/N-Gram): {jaccard_skipped} adet haber başlık benzerliği sebebiyle elendi ve kara listeye eklendi.")
            
    # ═══ KATMAN 3: Gemma 31B Batch Semantik Doğrulama ═══
    if new_news_list:
        print(f"\n🧠 Katman 3: {len(new_news_list)} adet yeni aday haber için Gemma Semantik Doğrulama başlatılıyor...")
        try:
            from ai_writer import check_news_semantic_duplicates
            
            # Adayları etiketle (id ekle) ve başlık + özet + kategori bilgilerini topla
            candidates_with_ids = []
            for i, item in enumerate(new_news_list, start=1):
                item["_id"] = i
                candidates_with_ids.append({
                    "id": i, 
                    "title": item["title"],
                    "summary": item["summary"][:300], # AI limitleri için özetin ilk 300 karakteri yeterlidir
                    "category": item["category"]
                })
                
            # Geriye dönük son 30 saatlik haberlerin başlıklarını AI'a gönder
            original_existing = get_existing_titles(hours_back=30)
            duplicate_ids = check_news_semantic_duplicates(candidates_with_ids, original_existing)
            
            if duplicate_ids:
                print(f"Gemma Semantik Doğrulama sonucunda {len(duplicate_ids)} adet haber elendi.")
                
                # Elenen haberlerin linklerini kara listeye ekle
                for item in new_news_list:
                    if item.get("_id") in duplicate_ids:
                        newly_blacklisted.append(item["link"])
                
                # Mükerrer olanları listeden çıkar
                original_count = len(new_news_list)
                new_news_list = [item for item in new_news_list if item["_id"] not in duplicate_ids]
                print(f"Haber listesi güncellendi: {original_count} -> {len(new_news_list)}")
            else:
                print("Gemma Semantik Doğrulama sonucunda mükerrer haber bulunmadı.")
                
            # Geçici id alanlarını temizle
            for item in new_news_list:
                item.pop("_id", None)
                
        except Exception as e:
            print(f"UYARI: Gemma Semantik Doğrulama adımı atlandı (Fallback aktif). Detay: {e}")
            # Hata durumunda geçici id'leri temizle ve yerel kararla devam et
            for item in new_news_list:
                item.pop("_id", None)
    
    # Kara listeye toplu yazım (tek Firestore write)
    if newly_blacklisted:
        try:
            firebase_helper.add_to_blacklist(newly_blacklisted)
        except Exception as e:
            print(f"UYARI: Kara listeye yazım başarısız oldu: {e}")
            
    # ═══ KATEGORİ BAŞINA MAKSİMUM 1 HABER KISITLAMASI ═══
    if new_news_list:
        category_picks = {}
        for item in new_news_list:
            cat = item["category"]
            if cat not in category_picks:
                category_picks[cat] = item
            else:
                print(f"Kategori Limiti: '{item['title']}' haberi, '{cat}' kategorisinde zaten 1 haber seçildiği için elendi.")
        new_news_list = list(category_picks.values())
            
    # ═══ KATMAN 4: Orijinal Görsel (og:image) Çekimi ═══
    if new_news_list:
        print(f"\n🖼️ Katman 4: Onaylanan {len(new_news_list)} haberin orijinal görselleri (og:image) aranıyor...")
        import requests
        from bs4 import BeautifulSoup
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        for item in new_news_list:
            try:
                res = requests.get(item["link"], headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, "html.parser")
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    item["og_image"] = og_img["content"]
                    print(f"  [+] Görsel bulundu: {item['title'][:30]}...")
                else:
                    item["og_image"] = None
                    print(f"  [-] Görsel bulunamadı: {item['title'][:30]}...")
            except Exception as e:
                print(f"  [!] UYARI: {item['title'][:30]} üzerinden og:image çekilemedi: {e}")
                item["og_image"] = None

    # Güncel veritabanını kaydet
    save_db(db_path, processed_links)
    print(f"\n✅ Toplam {len(new_news_list)} adet yeni haber onaylandı ve işlenmeye hazır.")
    print(f"📊 Filtre Raporu: Kara Liste={blacklist_skipped}, Jaccard={jaccard_skipped}, Kara Listeye Yeni Eklenen={len(newly_blacklisted)}")
    return new_news_list

if __name__ == "__main__":
    news = fetch_new_news()
    for item in news:
        print(f"- [{item['category'].upper()}] {item['title']} ({item['source']})")
