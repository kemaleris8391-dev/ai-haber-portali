import os
import re
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Çalışma dizinini ayarlayalım
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

load_dotenv(override=True)
import firebase_helper
import telegram_notifier

# API Anahtarlarını alalım
API_KEYS = []
keys_str = os.getenv("GEMINI_API_KEYS")
if keys_str:
    API_KEYS = [k.strip() for k in keys_str.split(",") if k.strip()]
else:
    fallback_key = os.getenv("GEMINI_API_KEY")
    if fallback_key:
        API_KEYS = [fallback_key.strip()]

current_key_idx = 0

def get_next_client():
    global current_key_idx
    if not API_KEYS:
        return genai.Client()
    api_key = API_KEYS[current_key_idx]
    return genai.Client(api_key=api_key)

def rotate_key():
    global current_key_idx
    if API_KEYS:
        current_key_idx = (current_key_idx + 1) % len(API_KEYS)

def clean_title_for_comparison(title):
    import re
    title = title.lower()
    title = re.sub(r"'[a-z0-9ıışşğğççööüü]*", "", title)
    tr_map = str.maketrans("çğıöşü", "cgiosu")
    title = title.translate(tr_map)
    title = re.sub(r'[^\w\s]', '', title)
    return title

def get_word_set(title):
    cleaned = clean_title_for_comparison(title)
    words = set(cleaned.split())
    stop_words = {
        "ve", "veya", "bir", "ile", "de", "da", "icin", "en", "bu", "o", "ise", "ki", 
        "yeni", "dev", "hakkinda", "neler", "nelerdir", "mi", "mu", "milyon", "milyar", 
        "kisi", "adet", "son", "ilk", "a", "an", "the", "of", "and", "in", "on", "at", "for"
    }
    return words - stop_words

def get_char_ngrams(title, n_list=[3, 4]):
    cleaned = "".join(clean_title_for_comparison(title).split())
    ngrams = set()
    for n in n_list:
        if len(cleaned) >= n:
            for i in range(len(cleaned) - n + 1):
                ngrams.add(cleaned[i:i+n])
    return ngrams

def check_mathematical_similarity(title1, title2, word_threshold=0.45, char_threshold=0.55):
    words1 = get_word_set(title1)
    words2 = get_word_set(title2)
    
    if not words1 or not words2:
        return False
        
    # Word Jaccard
    intersection_w = words1.intersection(words2)
    union_w = words1.union(words2)
    word_sim = len(intersection_w) / len(union_w) if union_w else 0.0
    
    # Char N-Gram Jaccard
    chars1 = get_char_ngrams(title1)
    chars2 = get_char_ngrams(title2)
    char_sim = 0.0
    if chars1 and chars2:
        intersection_c = chars1.intersection(chars2)
        union_c = chars1.union(chars2)
        char_sim = len(intersection_c) / len(union_c) if union_c else 0.0
        
    return word_sim >= word_threshold or char_sim >= char_threshold

def clean_body_text(content):
    # Frontmatter'ı ayır
    parts = content.split('---')
    body = ""
    if len(parts) >= 3:
        body = '---'.join(parts[2:])
    else:
        body = content
        
    # Markdown syntax temizliği
    body_clean = re.sub(r'#+\s+', '', body)
    body_clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', body_clean)
    body_clean = re.sub(r'[*_`]', '', body_clean)
    body_clean = re.sub(r'\s+', ' ', body_clean).strip()
    
    snippet = body_clean[:300]
    if len(body_clean) > 300:
        snippet += "..."
    return snippet

def get_news_from_recent_hours(blog_dir, hours):
    """Belirtilen saat periyodunda yayınlanan haberlerin listesini çeker."""
    if not os.path.exists(blog_dir):
        print(f"Hata: Blog dizini bulunamadı: {blog_dir}")
        return []
        
    filenames = [f for f in os.listdir(blog_dir) if f.endswith('.md')]
    recent_posts = []
    
    # Türkiye saatine göre naive datetime (UTC+3)
    tr_tz = timezone(timedelta(hours=3))
    now_tr = datetime.now(tr_tz).replace(tzinfo=None)
    
    for filename in filenames:
        filepath = os.path.join(blog_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Metadataları çekelim
            title_match = re.search(r'^title:\s*(["\'])(.*?)\1\s*$', content, re.MULTILINE)
            if not title_match:
                title_match = re.search(r'^title:\s*(.*?)\s*$', content, re.MULTILINE)
                
            pub_match = re.search(r'^pubDate:\s*(["\'])(.*?)\1\s*$', content, re.MULTILINE)
            if not pub_match:
                pub_match = re.search(r'^pubDate:\s*(.*?)\s*$', content, re.MULTILINE)
                
            category_match = re.search(r'^category:\s*(["\'])(.*?)\1\s*$', content, re.MULTILINE)
            if not category_match:
                category_match = re.search(r'^category:\s*(.*?)\s*$', content, re.MULTILINE)
                
            title = title_match.group(2) if title_match and len(title_match.groups()) >= 2 else (title_match.group(1) if title_match else "Başlık Yok")
            pub_val = pub_match.group(2) if pub_match and len(pub_match.groups()) >= 2 else (pub_match.group(1) if pub_match else "")
            category = category_match.group(2) if category_match and len(category_match.groups()) >= 2 else (category_match.group(1) if category_match else "teknoloji")
            
            title = title.strip('\'" ')
            pub_val = pub_val.strip('\'" ')
            category = category.strip('\'" ')
            
            if not pub_val:
                continue
                
            # pubDate parse edelim (ISO formatta örn: "2026-06-03T09:34:10")
            try:
                # timezone süzerek naive çevirelim
                dt_post = datetime.fromisoformat(pub_val[:19])
            except Exception:
                continue
                
            diff = now_tr - dt_post
            # Belirtilen saat + 1 saat esneklik payı
            if diff.total_seconds() <= (hours + 1) * 3600:
                recent_posts.append({
                    'filename': filename,
                    'title': title,
                    'category': category,
                    'pubDate': pub_val,
                    'snippet': clean_body_text(content),
                    'content': content
                })
        except Exception as e:
            print(f"Haber okunurken hata oluştu ({filename}): {e}")
            
    return recent_posts

def evaluate_batch_with_llm(batch_data, model_name="gemma-4-31b-it"):
    prompt = f"""
Aşağıda son periyotta eklenen haberler (dosya adı, başlık, kategori ve gövde özeti/snippet olarak) verilmiştir:
{json.dumps(batch_data, ensure_ascii=False, indent=2)}

GÖREV:
1. Bu haberlerin portalımızın yayın politikasına uygun olup olmadığını denetle.
   Yayın Politikası Odak Alanları:
   - Sadece PLC otomasyonu (plc), kişisel bilgisayarlar ve donanımlar (pc), endüstriyel makineler ve tamirleri (endustriyel-makinalar), oyun dünyası (oyun), yapay zeka (yapay-zeka) ve ev elektroniği/akıllı ev sistemleri (akilli-ev) hakkında olmalıdır.
   Politika Dışı (Uygun Olmayan) Alanlar:
   - Siyaset, politika, standart aşk/dram dizileri, magazin haberleri, genel otomotiv incelemeleri (elektrikli/otonom teknolojiler dışındaki standart araçlar), genel borsa/finans, yasal ihtilaflar, yemek tarifi vb.

2. Bu haberleri kendi aralarında analiz et. Eğer listede **semantik (anlamsal) olarak tamamen aynı gelişmeyi, lansmanı, duyuruyu veya olayı** ele alan mükerrer (kopya) haberler varsa, bunları tespit et.
   - Bir grupta mükerrer haberler varsa, aralarından en eski veya ana haberi temel kabul et (kalsın, duplicate_of değeri null olsun).
   - Diğer sonradan yazılan kopya haberlerin "duplicate_of" alanına bu temel haberin dosya adını yaz.

Çıktıyı KESİNLİKLE aşağıdaki JSON formatında ver (başka açıklama ekleme):
{{
  "results": [
    {{
      "filename": "haber-dosya-adi.md",
      "is_compliant": true,
      "reason": "Uygundur gerekçesi veya uygunsuzsa nedeni",
      "duplicate_of": "parent_filename.md" // Kopya değilse veya grubun ilk/ana haberiyse null olmalıdır
    }}
  ]
}}
"""
    max_retries = len(API_KEYS) if API_KEYS else 3
    last_error = ""
    
    # Sırasıyla denenecek modeller
    models_to_try = [model_name, "gemma-4-26b-a4b-it", "gemma-4-26b-it", "gemini-2.5-flash", "gemini-1.5-flash"]
    
    for current_model in models_to_try:
        for attempt in range(max_retries):
            client = get_next_client()
            try:
                masked_key = f"...{API_KEYS[current_key_idx][-6:]}" if API_KEYS else "default"
                print(f"Yapay Zeka analizi yapılıyor. Model: {current_model} (Key: {masked_key})")
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if response.text:
                    try:
                        return json.loads(response.text.strip()), current_model
                    except Exception:
                        clean_text = response.text.replace("```json", "").replace("```", "").strip()
                        return json.loads(clean_text), current_model
            except Exception as e:
                last_error = str(e)
                print(f"Model {current_model} ile Hata (Deneme {attempt + 1}/{max_retries}): {last_error}")
                rotate_key()
                if "429" in last_error or "Quota" in last_error:
                    time.sleep(2)
                
    # Tüm denemeler başarısız olduysa hata fırlatalım
    raise Exception(f"AI model denemeleri başarısız oldu. Son hata: {last_error}")

def delete_post_files(blog_dir, public_images_dir, filename, content):
    """Haber dosyasını ve ilişkili kapak resmini diskten siler."""
    markdown_path = os.path.join(blog_dir, filename)
    image_deleted = False
    
    # Kapak resmini silme
    image_match = re.search(r'^heroImage:\s*(["\'])(.*?)\1\s*$', content, re.MULTILINE)
    if not image_match:
        image_match = re.search(r'^heroImage:\s*(.*?)\s*$', content, re.MULTILINE)
        
    if image_match:
        image_path = image_match.group(2) if len(image_match.groups()) >= 2 else image_match.group(1)
        image_path = image_path.strip('\'" ')
        
        # Eğer resim yerel ise sil
        if image_path.startswith('/images/news/'):
            # leading slashi temizle
            rel_image_path = image_path[1:]
            full_image_path = os.path.join(public_images_dir, rel_image_path)
            if os.path.exists(full_image_path):
                try:
                    os.remove(full_image_path)
                    image_deleted = True
                except Exception as img_err:
                    print(f"Resim silinemedi {image_path}: {img_err}")
                    
    # Markdown dosyasını sil
    if os.path.exists(markdown_path):
        try:
            os.remove(markdown_path)
            return True, image_deleted
        except Exception as md_err:
            print(f"Markdown silinemedi {filename}: {md_err}")
            
    return False, False

def run_auto_cleanup_if_needed(config_dict, force=False):
    """Ana otonom temizlik kontrol fonksiyonu."""
    print("Otonom temizlik kontrolü başlatılıyor...")
    
    try:
        cleanup_config = firebase_helper.get_cleanup_config()
    except Exception as fs_err:
        print(f"Firestore otonom temizlik konfigürasyonu alınamadı: {fs_err}")
        return
        
    is_active = cleanup_config.get("is_active", True)
    interval_hours = cleanup_config.get("interval_hours", 24)
    last_cleanup = cleanup_config.get("last_cleanup_time", 0.0)
    
    now = time.time()
    elapsed_hours = (now - last_cleanup) / 3600.0
    
    if not force:
        if not is_active:
            print("Otonom haber temizliği devre dışı (Pasif).")
            return
        if elapsed_hours < interval_hours:
            remaining = int(interval_hours - elapsed_hours)
            print(f"Otonom temizlik için henüz süre dolmadı. Kalan: {remaining} saat.")
            return
            
    print(f"Temizlik zamanı geldi! Başlatılıyor. Zorlama: {force}")
    
    # Dizinleri belirleyelim
    output_dir = config_dict["settings"]["output_dir"]
    images_dir = config_dict["settings"]["images_dir"]
    
    blog_dir = os.path.abspath(os.path.join(base_dir, output_dir))
    public_images_dir = os.path.abspath(os.path.join(base_dir, "..", "web-portal/public"))
    
    # 1. Belirlenen periyot saatindeki haberleri listele
    recent_news = get_news_from_recent_hours(blog_dir, interval_hours)
    total_recent = len(recent_news)
    
    if total_recent == 0:
        print(f"Son {interval_hours} saatte yayınlanan haber bulunmadı. Temizlik tamam.")
        firebase_helper.update_cleanup_config(last_cleanup_time=now)
        if force:
            telegram_notifier.send_success(
                "Otonom Temizlik Raporu",
                f"Son {interval_hours} saatte taranacak haber bulunmadığı için temizlik yapılmadı."
            )
        return
        
    # Kronolojik olarak sırala (en eski haber orijinal kabul edilsin)
    recent_news.sort(key=lambda x: x.get("pubDate", ""))
    
    # Yerel Matematiksel Jaccard / N-Gram Ön-Benzerlik Kontrolü
    pre_filtered_duplicates = {}
    news_to_analyze = []
    
    print("Yerel matematiksel benzerlik ön-taraması başlatılıyor...")
    for idx, item in enumerate(recent_news):
        is_dup = False
        duplicate_parent = ""
        # Kendinden önceki (daha eski) haberlerle karşılaştır
        for prev_item in recent_news[:idx]:
            if prev_item["filename"] in pre_filtered_duplicates:
                continue # Zaten mükerrer olanla kıyaslama yapma
            if check_mathematical_similarity(item["title"], prev_item["title"]):
                is_dup = True
                duplicate_parent = prev_item["filename"]
                break
                
        if is_dup:
            print(f"Pre-Filter: '{item['title']}' haberi, '{duplicate_parent}' ile benzer bulundu (Mükerrer).")
            pre_filtered_duplicates[item["filename"]] = f"Matematiksel Mükerrer ({duplicate_parent} ile çakışıyor)"
        else:
            news_to_analyze.append(item)
            
    total_to_analyze = len(news_to_analyze)
    print(f"Matematiksel ön-tarama sonucu: {len(pre_filtered_duplicates)} haber elendi. {total_to_analyze} haber AI analizine gönderilecek.")
    
    # 2. Kalan haberleri paketler halinde analiz et (25 limitli batch'ler)
    all_results = []
    models_used = set()
    
    if total_to_analyze > 0:
        batch_size = 25
        batches = [news_to_analyze[i:i + batch_size] for i in range(0, total_to_analyze, batch_size)]
        
        for i, batch in enumerate(batches, 1):
            print(f"Haber paketi gönderiliyor ({i}/{len(batches)}) ({len(batch)} haber)...")
            batch_input = [
                {
                    "filename": item["filename"],
                    "title": item["title"],
                    "category": item["category"],
                    "pubDate": item["pubDate"],
                    "snippet": item["snippet"]
                } for item in batch
            ]
            
            try:
                res, used_model = evaluate_batch_with_llm(batch_input, model_name="gemma-4-31b-it")
                models_used.add(used_model)
                if "results" in res:
                    all_results.extend(res["results"])
            except Exception as e:
                print(f"Haber paketi işlenirken hata oluştu: {e}")
    else:
        print("AI analizine gönderilecek haber kalmadı. Sadece ön-filtre silmeleri uygulanacak.")
            
    # 3. Sonuçları değerlendirip silmeleri uygulayalım
    deleted_posts = []
    deleted_images_count = 0
    
    news_map = {item["filename"]: item for item in recent_news}
    
    # Silineceklerin listesini topla
    to_delete_list = []
    
    for result in all_results:
        filename = result.get("filename")
        is_compliant = result.get("is_compliant", True)
        duplicate_of = result.get("duplicate_of")
        reason = result.get("reason", "")
        
        if filename not in news_map:
            continue
            
        should_delete = False
        delete_reason = ""
        
        if not is_compliant:
            should_delete = True
            delete_reason = f"Yayın Politikası Dışı: {reason}"
        elif duplicate_of and duplicate_of in news_map:
            should_delete = True
            delete_reason = f"Mükerrer ({duplicate_of} haberi ile çakışıyor): {reason}"
            
        if should_delete:
            to_delete_list.append((filename, delete_reason))
            
    # Ön-filtre ile elenen matematiksel mükerrerleri de silme listesine ekle
    for filename, delete_reason in pre_filtered_duplicates.items():
        if filename not in [x[0] for x in to_delete_list]:
            to_delete_list.append((filename, delete_reason))
            
    # Paralel asenkron dosya silme (ThreadPoolExecutor)
    import concurrent.futures
    if to_delete_list:
        print(f"Paralel silme işlemi başlatılıyor ({len(to_delete_list)} dosya)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(
                    delete_post_files,
                    blog_dir,
                    public_images_dir,
                    filename,
                    news_map[filename]["content"]
                ): (filename, delete_reason) for filename, delete_reason in to_delete_list
            }
            
            for future in concurrent.futures.as_completed(futures):
                filename, delete_reason = futures[future]
                try:
                    success, img_del = future.result()
                    if success:
                        item = news_map[filename]
                        deleted_posts.append({
                            "title": item["title"],
                            "filename": filename,
                            "reason": delete_reason
                        })
                        if img_del:
                            deleted_images_count += 1
                except Exception as del_err:
                    print(f"HATA: {filename} silinirken sorun oluştu: {del_err}")
                    
    # 4. Rapor ve Bildirim gönder
    firebase_helper.update_cleanup_config(last_cleanup_time=now)
    
    models_str = ", ".join(models_used)
    report = (
        f"🧹 <b>Otonom Haber Temizlik Raporu</b>\n"
        f"──────────────────────────────\n"
        f"📋 <b>İncelenen Haber (Son {interval_hours} Saat):</b> {total_recent} adet\n"
        f"🤖 <b>Kullanılan AI Modeli:</b> <code>{models_str}</code>\n"
    )
    
    if deleted_posts:
        details = ""
        for idx, post in enumerate(deleted_posts, start=1):
            details += f"\n<b>{idx}. {post['title']}</b>\n"
            details += f"📄 Dosya: <code>{post['filename']}</code>\n"
            details += f"⚠️ Gerekçe: <i>{post['reason']}</i>\n"
            
        report += (
            f"🗑️ <b>Silinen Haber Sayısı:</b> {len(deleted_posts)} adet\n"
            f"🖼️ <b>Silinen Resim Sayısı:</b> {deleted_images_count} adet\n"
            f"──────────────────────────────\n"
            f"👇 <b>Silinen İçerik Detayları:</b>\n"
            f"{details}\n\n"
            f"🚀 Canlı siteniz otomatik olarak yeniden derlenip güncellenmektedir."
        )
        telegram_notifier.send_success("Otonom Temizlik Raporu - Müdahale Edildi!", report)
    else:
        report += (
            f"🟢 <b>Durum:</b> Hiçbir aykırı veya mükerrer haber <b>tespit edilmedi.</b>\n"
            f"✅ Sitemiz tamamen temiz durumdadır."
        )
        # Sadece force olduğunda veya belirli aralıklarla spam olmaması için
        telegram_notifier.send_success("Otonom Temizlik Raporu - Sistem Temiz!", report)

if __name__ == "__main__":
    # Test etmek için direkt çalıştırılabilir
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    from fetcher import load_config
    config = load_config()
    run_auto_cleanup_if_needed(config, force=True)
