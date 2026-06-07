import os
import json
import time
import re
import difflib
import concurrent.futures
import html
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
import requests
import feedparser
import firebase_admin
from firebase_admin import credentials, firestore
from google import genai
from google.genai import types


# Firebase Firestore client initialization
db_client = None

def init_firebase():
    """Initializes Firebase Admin SDK and returns Firestore client."""
    global db_client
    if db_client is not None:
        return db_client

    try:
        app = firebase_admin.get_app()
    except ValueError:
        # Not initialized yet, let's do it using credentials
        cred_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

        if cred_env:
            try:
                cred_dict = json.loads(cred_env)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"HATA: FIREBASE_SERVICE_ACCOUNT_JSON ayrıştırılamadı: {e}")
                firebase_admin.initialize_app()
        else:
            firebase_admin.initialize_app()

    db_client = firestore.client()
    return db_client

# DATABASE HELPER METHODS
def get_scheduler_config():
    """Fetches scheduler config from Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("scheduler")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        interval = data.get("interval_minutes", 20)
        last_run = data.get("last_run_time", time.time())
        is_running = data.get("is_running", False)
        is_active = data.get("is_active", True)
        return {
            "interval_minutes": int(interval),
            "last_run_time": float(last_run),
            "is_running": bool(is_running),
            "is_active": bool(is_active)
        }
    else:
        default_config = {
            "interval_minutes": 20,
            "last_run_time": time.time(),
            "is_running": False,
            "is_active": True
        }
        doc_ref.set(default_config)
        return default_config

def update_scheduler_config(interval_minutes=None, last_run_time=None, is_running=None, is_active=None):
    """Updates scheduler config on Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("scheduler")
    
    update_data = {}
    if interval_minutes is not None:
        update_data["interval_minutes"] = int(interval_minutes)
    if last_run_time is not None:
        update_data["last_run_time"] = float(last_run_time)
    if is_running is not None:
        update_data["is_running"] = bool(is_running)
    if is_active is not None:
        update_data["is_active"] = bool(is_active)
        
    if update_data:
        doc_ref.update(update_data)

def get_cleanup_config():
    """Fetches cleanup config from Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("auto_cleanup")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        interval_hours = data.get("interval_hours", 24)
        last_cleanup_time = data.get("last_cleanup_time", 0.0)
        is_active = data.get("is_active", True)
        return {
            "interval_hours": int(interval_hours),
            "last_cleanup_time": float(last_cleanup_time),
            "is_active": bool(is_active)
        }
    else:
        default_config = {
            "interval_hours": 24,
            "last_cleanup_time": 0.0,
            "is_active": True
        }
        doc_ref.set(default_config)
        return default_config

def update_cleanup_config(interval_hours=None, last_cleanup_time=None, is_active=None):
    """Updates cleanup config on Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("auto_cleanup")
    
    update_data = {}
    if interval_hours is not None:
        update_data["interval_hours"] = int(interval_hours)
    if last_cleanup_time is not None:
        update_data["last_cleanup_time"] = float(last_cleanup_time)
    if is_active is not None:
        update_data["is_active"] = bool(is_active)
        
    if update_data:
        doc_ref.set(update_data, merge=True)

def get_rss_sources():
    """Fetches RSS sources from Firestore."""
    db = init_firebase()
    sources_ref = db.collection("rss_sources")
    docs = sources_ref.stream()
    
    sources = []
    for doc in docs:
        data = doc.to_dict()
        sources.append({
            "name": data.get("name"),
            "url": data.get("url"),
            "category": data.get("category")
        })
    return sources

def add_rss_source(name, url, category):
    """Adds a new RSS source to Firestore."""
    db = init_firebase()
    doc_id = "".join(c for c in name.lower() if c.isalnum() or c == "_")
    doc_ref = db.collection("rss_sources").document(doc_id)
    doc_ref.set({
        "name": name,
        "url": url,
        "category": category
    })
    return True

def delete_rss_source(name):
    """Deletes an RSS source from Firestore."""
    db = init_firebase()
    doc_id = "".join(c for c in name.lower() if c.isalnum() or c == "_")
    doc_ref = db.collection("rss_sources").document(doc_id)
    if doc_ref.get().exists:
        doc_ref.delete()
        return True
    return False

def slugify(text):
    text = text.lower().strip()
    chars = {
        "ö": "o", "ü": "u", "ş": "s", "ç": "c", "ğ": "g", "ı": "i",
        "Ö": "o", "Ü": "u", "Ş": "s", "Ç": "c", "Ğ": "g", "İ": "i"
    }
    for k, v in chars.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

def discover_rss_feed(site_url):
    if not site_url.startswith("http"):
        site_url = "https://" + site_url
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        r = requests.get(site_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
            
        html = r.text
        rss_links = []
        
        from urllib.parse import urljoin
        for match_str in re.findall(r'<link[^>]+>', html, re.IGNORECASE):
            href_m = re.search(r'href=["\'](.*?)["\']', match_str, re.IGNORECASE)
            type_m = re.search(r'type=["\'](application/(rss|atom)\+xml)["\']', match_str, re.IGNORECASE)
            title_m = re.search(r'title=["\'](.*?)["\']', match_str, re.IGNORECASE)
            
            if href_m and type_m:
                feed_url = href_m.group(1).strip()
                feed_url = urljoin(site_url, feed_url)
                title = title_m.group(1).strip() if title_m else "RSS Feed"
                rss_links.append((title, feed_url))
                
        if not rss_links:
            common_paths = ["/feed", "/rss", "/rss.xml", "/feed.xml", "/index.xml"]
            for path in common_paths:
                test_url = urljoin(site_url, path)
                try:
                    res = requests.get(test_url, headers=headers, timeout=5)
                    if res.status_code == 200 and ("xml" in res.headers.get("Content-Type", "").lower() or "<rss" in res.text[:200].lower() or "<feed" in res.text[:200].lower()):
                        rss_links.append(("Feed", test_url))
                        break
                except:
                    continue
                    
        return rss_links
    except Exception as e:
        print(f"Error discovering RSS feed: {e}")
        return []

def verify_and_parse_feed(feed_url):
    import feedparser
    try:
        r = requests.get(feed_url, timeout=10)
        feed = feedparser.parse(r.text)
        if feed.entries:
            title = feed.feed.get("title", "RSS Kaynağı")
            return True, title
    except Exception as e:
        print(f"Error parsing feed: {e}")
    return False, None

def get_categories():
    db = init_firebase()
    doc = db.collection("system_config").document("categories").get()
    if doc.exists:
        return doc.to_dict().get("list", ["teknoloji", "oyun", "dizi-film"])
    else:
        default_cats = ["teknoloji", "oyun", "dizi-film"]
        db.collection("system_config").document("categories").set({"list": default_cats})
        return default_cats

def add_category(cat_name):
    db = init_firebase()
    cats = get_categories()
    cat_slug = slugify(cat_name)
    cat_slug = "".join(c for c in cat_slug.lower() if c.isalnum() or c == "-")
    if cat_slug not in cats:
        cats.append(cat_slug)
        db.collection("system_config").document("categories").set({"list": cats})
        return True, cat_slug
    return False, cat_slug

def delete_category(cat_slug):
    db = init_firebase()
    cats = get_categories()
    if cat_slug in cats:
        cats.remove(cat_slug)
        db.collection("system_config").document("categories").set({"list": cats})
        return True
    return False

# --- INDEX AND INTERACTIVE DELETION HELPER METHODS ---
def extract_metadata_from_markdown(content):
    title = "Bilinmeyen Haber"
    pub_date = "2026-05-30"
    hero_image = "/images/default-news.png"
    category = "teknoloji"
    
    title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
    pub_match = re.search(r'^pubDate:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
    image_match = re.search(r'^heroImage:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
    category_match = re.search(r'^category:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
    
    if title_match:
        title = title_match.group(1).strip()
    pub_datetime = ""
    if pub_match:
        pub_val = pub_match.group(1).strip()
        if len(pub_val) >= 10:
            pub_date = pub_val[:10]
        if len(pub_val) >= 16:
            pub_datetime = pub_val
    if image_match:
        hero_image = image_match.group(1).strip()
    if category_match:
        category = category_match.group(1).strip().lower()
        
    return title, pub_date, hero_image, category, pub_datetime

def rebuild_posts_index():
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    path = "web-portal/src/content/blog"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AIHABERLER-Bot"
    }
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token.strip()}"
        
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise Exception(f"GitHub Contents API failed: {r.status_code} {r.text}")
        
    files = r.json()
    md_files = [f for f in files if f.get("name", "").endswith(".md")]
    
    posts = {}
    
    def process_file(f_info, p_id):
        f_name = f_info["name"]
        f_sha = f_info["sha"]
        f_path = f_info["path"]
        
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{f_path}"
        try:
            range_headers = {"Range": "bytes=0-1000"}
            res = requests.get(raw_url, headers=range_headers, timeout=8)
            if res.status_code in [200, 206]:
                content = res.text
                title, pub_date, hero_image, category, pub_datetime = extract_metadata_from_markdown(content)
                return p_id, {
                    "slug": f_name,
                    "title": title,
                    "date": pub_date,
                    "pubDateTime": pub_datetime,
                    "image": hero_image,
                    "category": category,
                    "sha": f_sha
                }
        except Exception as err:
            print(f"Error fetching raw file {f_name}: {err}")
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = []
        for i, f_info in enumerate(md_files, start=1):
            p_id = f"p{i}"
            futures.append(executor.submit(process_file, f_info, p_id))
            
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                p_id, p_info = res
                posts[p_id] = p_info
                
    index_data = {
        "last_updated": time.time(),
        "posts": posts
    }
    
    db = init_firebase()
    db.collection("system_config").document("posts_index").set(index_data)
    return index_data

def get_posts_index(force_rebuild=False):
    db = init_firebase()
    doc_ref = db.collection("system_config").document("posts_index")
    doc = doc_ref.get()
    
    if doc.exists and not force_rebuild:
        return doc.to_dict()
            
    print("Rebuilding posts index...")
    try:
        return rebuild_posts_index()
    except Exception as e:
        print(f"Error rebuilding index: {e}")
        if doc.exists:
            print("Falling back to existing Firestore index.")
            return doc.to_dict()
        raise e

def remove_posts_from_index_locally(p_ids):
    """Removes a list of post IDs from the Firestore posts_index document locally in-memory."""
    try:
        db = init_firebase()
        doc_ref = db.collection("system_config").document("posts_index")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            posts = data.get("posts", {})
            updated = False
            for p_id in p_ids:
                if p_id in posts:
                    del posts[p_id]
                    updated = True
            if updated:
                data["last_updated"] = time.time()
                doc_ref.set(data)
                print(f"Locally removed {len(p_ids)} posts from posts_index in Firestore.")
                return True
    except Exception as e:
        print(f"Error removing posts from index locally: {e}")
    return False

def get_or_init_multi_delete_state(chat_id, context, metadata=None):
    """Gets or initializes the multi_delete state in the bot_state document in Firestore."""
    try:
        db = init_firebase()
        doc_ref = db.collection("system_config").document("bot_state")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if data.get("state") == "multi_delete" and data.get("context") == context:
                # Check if metadata matches (for sil date/category)
                if context == "sil":
                    meta = data.get("metadata", {})
                    new_meta = metadata or {}
                    if meta.get("date") == new_meta.get("date") and meta.get("category") == new_meta.get("category"):
                         return data.get("selected_ids", [])
                else:
                    return data.get("selected_ids", [])
        
        # Initialize new state
        init_data = {
            "state": "multi_delete",
            "chat_id": str(chat_id),
            "selected_ids": [],
            "context": context
        }
        if metadata:
            init_data["metadata"] = metadata
        doc_ref.set(init_data)
        return []
    except Exception as e:
        print(f"Error managing bot state: {e}")
        return []

def edit_message_text(text, message_id, reply_markup=None, chat_id=None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not chat_id:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
    if not bot_token or not chat_id:
        return
        
    url = f"https://api.telegram.org/bot{bot_token.strip()}/editMessageText"
    payload = {
        "chat_id": str(chat_id).strip(),
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            resp_json = {}
            try:
                resp_json = r.json()
            except:
                pass
            desc = resp_json.get("description", "")
            if "message is not modified" in desc:
                # Sessizce yutalım, hata değil
                print("Bilgi: Telegram mesajı değiştirilmedi (aynı içerik).")
                return
            print(f"HATA: Telegram editMessageText API yanıtı: {r.status_code} - {r.text}")
            r.raise_for_status()
    except Exception as e:
        print(f"Error editing message: {e}")
        raise e

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return
    url = f"https://api.telegram.org/bot{bot_token.strip()}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }
    if text:
        payload["text"] = text
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error answering callback: {e}")

def clean_title_for_similarity(title):
    title = title.lower()
    tr_map = str.maketrans("çğıöşü", "cgiosu")
    title = title.translate(tr_map)
    title = re.sub(r'[^a-z0-9\s]', ' ', title)
    words = title.split()
    stop_words = {'ve', 'ile', 'de', 'da', 'bir', 'icin', 'en', 'son', 'bu', 'olan', 'olarak', 'yeni', 'guncel'}
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    return filtered_words, title

def calculate_title_similarity(title1, title2):
    words1, clean1 = clean_title_for_similarity(title1)
    words2, clean2 = clean_title_for_similarity(title2)
    
    if not words1 or not words2:
        return 0.0
        
    set1, set2 = set(words1), set(words2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    jaccard = len(intersection) / len(union) if union else 0
    
    seq = difflib.SequenceMatcher(None, clean1, clean2)
    seq_ratio = seq.ratio()
    
    # Combined score
    score = (jaccard * 0.6) + (seq_ratio * 0.4)
    return score

def check_similar_news_locally():
    index_data = get_posts_index()
    posts = index_data.get("posts", {})
    if not posts:
        return "BENZER_HABER_YOK", []
        
    posts_with_ids = list(posts.items())
    sorted_posts = sorted(
        posts_with_ids, 
        key=lambda x: (x[1].get("pubDateTime", x[1].get("date", "")), x[1].get("slug", "")), 
        reverse=True
    )
    
    # Calculate today and yesterday in Turkey timezone
    from datetime import timezone, timedelta
    tr_tz = timezone(timedelta(hours=3))
    today_str = datetime.now(tr_tz).strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(tr_tz) - timedelta(days=1)).strftime("%Y-%m-%d")
    valid_dates = {today_str, yesterday_str}
    
    # Filter today's and yesterday's posts to satisfy "only look at the last day"
    recent_posts = [p for p in sorted_posts if p[1].get("date") in valid_dates]
    
    if len(recent_posts) < 2:
        return "BENZER_HABER_YOK", []
        
    # Prepare API keys
    api_keys = []
    keys_str = os.getenv("GEMINI_API_KEYS")
    if keys_str:
        api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    else:
        fallback_key = os.getenv("GEMINI_API_KEY")
        if fallback_key:
            api_keys = [fallback_key.strip()]
            
    if not api_keys:
        print("HATA: Benzer haber kontrolü için GEMINI_API_KEYS veya GEMINI_API_KEY bulunamadı!")
        return "❌ <b>API Anahtarları Bulunamadı.</b>", []
        
    # Format inputs for Gemma
    posts_input = [{"id": p_id, "title": p["title"]} for p_id, p in recent_posts]
    
    prompt = f"""
Aşağıda sitemizde son 24-48 saat içinde yayınlanmış olan haberlerin başlıkları verilmiştir.

GÖREV:
Bu haberleri analiz et. Eğer listede **semantik (anlamsal) olarak tamamen AYNI gelişmeyi, aynı lansmanı, aynı ürün duyurusunu, aynı fragman haberini veya aynı olay duyurusunu** ele alan mükerrer (kopya) haberler varsa, bunları grupla.
Her grupta en az 2 haber bulunmalıdır.

GRUPLAMA KURALLARI (MANDATORY - KESİNLİKLE UYULMALIDIR):
1. **Birebir Aynı Olay Olmalıdır:** Sadece başlığı benzediği için haberleri eşleştirme. Örneğin "Audi fiyat listesi" ile "Togg fiyat listesi" farklı olaylardır, eşleştirme! "Amazon Prime Oyunları" ile "Xbox Game Pass Oyunları" farklıdır, eşleştirme! "Aselsan milli takım sponsoru oldu" ile "Gemini milli takım sponsoru oldu" farklıdır, eşleştirme!
2. **Semantik Eşleşme:** Başlıklar farklı kelimelerle ifade edilmiş olsa bile semantik olarak aynı olayı anlatıyorsa eşleştir. Örneğin:
   - "Control 2 Çıkış Tarihi Duyuruldu" ile "Beklenen An Geldi: Control 2 Ne Zaman Çıkıyor?" semantik olarak AYNI haberdir, eşleştir.
   - "Scary Movie Geri Dönüyor" ile "Korkunç Bir Film Efsanesi Yeniden Sinemalarda" AYNI haberdir, eşleştir.
3. **Farklı Açılar/Aşamalar:** Aynı konu hakkında ama farklı günlerdeki farklı aşamaları anlatan haberleri (örn: "Modern Warfare 4 Duyuruldu" ile "Modern Warfare 4 Satış Rekoru Kırdı") eşleştirme, bunlar farklı haberlerdir.

Girdiler:
{json.dumps(posts_input, ensure_ascii=False, indent=2)}

Çıktıyı KESİNLİKLE aşağıdaki JSON formatında ver:
{{
  "groups": [
    {{
      "reason": "İki haber de ... konusundaki aynı lansmanı/duyuruyu anlatıyor.",
      "post_ids": ["p1", "p2", ...]
    }}
  ]
}}
"""
    
    # Gemma REST call payload using GenAI SDK
    response_text = ""
    last_err = "Bilinmeyen API Hatası"
    for key in api_keys:
        try:
            print(f"Gemma 31B ile semantik analizi yapılıyor (Key: {key[-6:]})...")
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemma-4-31b-it",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            response_text = response.text
            if response_text:
                break
        except Exception as e:
            last_err = str(e)
            print(f"Gemma API hatası (Key: {key[-6:]}): {last_err}")
            
    if not response_text:
        print(f"Gemma 31B semantik mükerrer araması başarısız: {last_err}")
        return "❌ <b>Gemma 31B Semantik Analiz Servisi Geçici Olarak Yanıt Vermiyor.</b>", []
        
    try:
        # Parse JSON from Gemma response
        data = json.loads(response_text.strip())
        groups = data.get("groups", [])
    except Exception as parse_err:
        print(f"Gemma JSON ayrıştırma hatası: {parse_err}. Yanıt: {response_text}")
        return "❌ <b>Semantik Analiz Çıktısı Ayrıştırılamadı.</b>", []
        
    similar_groups = []
    # Build list of groups with actual post data dictionaries
    for g in groups:
        p_ids = g.get("post_ids", [])
        reason = g.get("reason", "Anlamsal mükerrerlik")
        
        group_posts = []
        for pid in p_ids:
            # Find the post in recent_posts
            for item_id, item_data in recent_posts:
                if item_id == pid:
                    group_posts.append((item_id, item_data))
                    break
                    
        if len(group_posts) > 1:
            similar_groups.append((reason, group_posts))
            
    if not similar_groups:
        return "BENZER_HABER_YOK", []
        
    report = "🤖 <b>Gemma 31B Semantik Mükerrer Analiz Raporu</b>\n"
    report += "──────────────────────────────\n"
    report += "🔍 <i>Gemma 4 31B modeli son 24-48 saatlik haberlerinizi semantik olarak inceledi ve birebir çakışan grupları buldu:</i>\n\n"
    
    flat_duplicate_posts = []
    
    for idx, (reason, group_posts) in enumerate(similar_groups[:5], 1):
        # Sort group by pubDateTime ascending (earliest = original)
        sorted_group = sorted(
            group_posts, 
            key=lambda x: (x[1].get("pubDateTime", x[1].get("date", "")), x[1].get("slug", ""))
        )
        original_p_id = sorted_group[0][0]
        
        report += f"📦 <b>Benzer Haber Grubu #{idx}</b>\n"
        for p_id, p in sorted_group:
            pdt = p.get("pubDateTime", "")
            time_display = ""
            if pdt and len(pdt) >= 16:
                time_display = pdt[11:16]  # HH:MM
            
            escaped_title = html.escape(p['title'])
            if p_id == original_p_id:
                report += f"✅ <code>[{p['date']} {time_display}]</code> <b>İLK HABER (ORJİNAL)</b> {escaped_title} <i>({p.get('category', 'teknoloji').upper()})</i>\n"
            else:
                report += f"🗑️ <code>[{p['date']} {time_display}]</code> {escaped_title} <i>({p.get('category', 'teknoloji').upper()})</i>\n"
                flat_duplicate_posts.append((p_id, p))
                
        report += f"⚠️ <b>Gemma Analiz Nedeni:</b> <i>{html.escape(reason)}</i>\n"
        report += "──────────────────────────────\n"
        
    if len(similar_groups) > 5:
        report += f"💡 <i>Not: Toplam {len(similar_groups)} semantik mükerrer grup bulundu. Limitler gereği ilk 5 grup listelenmektedir.</i>\n"
        
    # Sort flat duplicate list by pubDateTime (newest first)
    flat_duplicate_posts = sorted(
        flat_duplicate_posts, 
        key=lambda x: (x[1].get("pubDateTime", x[1].get("date", "")), x[1].get("slug", "")), 
        reverse=True
    )
    return report, flat_duplicate_posts

def handle_benzer_haber_callback(callback_query, is_toggle=False):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    if not is_toggle:
        edit_message_text("🔍 <b>Gemma 31B semantik motoru haberlerinizi analiz ediyor...</b>\n\n(Lütfen bekleyin, son 24-48 saatlik (bugün+dün) haber başlıkları taranıyor ve mükerrer yakınlık kontrolü yapılıyor)", message_id)
        answer_callback_query(callback_id, "Analiz başlatıldı.")
        
    try:
        analysis_result, duplicate_posts = check_similar_news_locally()
        
        selected_ids = get_or_init_multi_delete_state(chat_id, "benzer")
        
        if "BENZER_HABER_YOK" in analysis_result or not duplicate_posts:
            success_text = (
                "🟢 <b>Benzer Haber Bulunmadı!</b>\n\n"
                "Sitenizdeki son 24-48 saatlik (bugün+dün) haber başlıkları Gemma 31B semantik motoru tarafından taranmıştır.\n\n"
                "✅ Birbiriyle çakışan, mükerrer veya aşırı benzeyen hiçbir kopya haber **tespit edilmemiştir!** Sisteminiz tamamen temiz durumdadır."
            )
            keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
            edit_message_text(success_text, message_id, reply_markup={"inline_keyboard": keyboard})
        else:
            warning_text = (
                "⚠️ <b>Benzer/Mükerrer Haberler Tespit Edildi!</b>\n\n"
                f"{analysis_result}\n"
                "👇 <b>Silmek istediğiniz mükerrer haberleri seçin:</b>"
            )
            
            # Build buttons for duplicate posts
            keyboard = []
            for p_id, p in duplicate_posts:
                title = p["title"]
                if len(title) > 35:
                    title = title[:32] + "..."
                # Short date format like "31 May"
                pdt = p.get("pubDateTime", p["date"])
                try:
                    if len(pdt) >= 16:
                        dt = datetime.strptime(pdt[:16], "%Y-%m-%dT%H:%M")
                    else:
                        dt = datetime.strptime(pdt[:10], "%Y-%m-%d")
                    tr_months = {
                        1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
                        7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"
                    }
                    if len(pdt) >= 16:
                        date_display = f"{dt.day} {tr_months[dt.month]} {dt.hour:02d}:{dt.minute:02d}"
                    else:
                        date_display = f"{dt.day} {tr_months[dt.month]}"
                except:
                    date_display = pdt[-5:]
                    
                icon = "✅" if p_id in selected_ids else "⬜"
                keyboard.append([{"text": f"{icon} [{date_display}] {title}", "callback_data": f"toggle:{p_id}"}])
                
            delete_btn_text = f"🗑️ Seçilenleri Sil ({len(selected_ids)} adet)" if selected_ids else "🗑️ Seçilenleri Sil"
            keyboard.append([{"text": delete_btn_text, "callback_data": "confirm_multi_del"}])
            keyboard.append([{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}])
            
            edit_message_text(warning_text, message_id, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        send_error("Benzer Haber Tarama Hatası", f"Hata: {e}")

def send_professional_help_dashboard(message_id=None):
    text = (
        "🤖 <b>AIHABERLER OTONOM YÖNETİM MERKEZİ</b> 🤖\n"
        "──────────────────────────────\n"
        "✨ <i>Yapay Zeka ve Bulut Teknolojileri ile Güçlendirilmiş Akıllı Haber Portalı Yönetim Paneline Hoş Geldiniz!</i>\n\n"
        "Tüm sistem komutlarını aşağıdaki interaktif butonlar aracılığıyla <b>hiçbir şey yazmadan</b>, sadece tıklayarak yönetebilirsiniz:\n"
        "──────────────────────────────\n"
        "🔗 <b>Portal Adresi:</b> https://aihaberler.web.app"
    )
    
    keyboard = [
        [
            {"text": "📊 Sistem Durumu", "callback_data": "menu:durum"},
            {"text": "⚡ Anlık RSS Tara", "callback_data": "menu:tara"}
        ],
        [
            {"text": "⏱️ Tarama Sıklığı", "callback_data": "menu:sure"},
            {"text": "🟢🔴 Otonom Aç/Kapa", "callback_data": "menu:otonom"}
        ],
        [
            {"text": "📋 RSS Kaynakları", "callback_data": "menu:rss"},
            {"text": "🗑️ Haber Sil (İnteraktif)", "callback_data": "menu:sil"}
        ],
        [
            {"text": "🔍 Benzer Haber Ara", "callback_data": "menu:benzer"},
            {"text": "🧹 Oto Temizlik", "callback_data": "menu:ototemizleme"}
        ]
    ]
    
    reply_markup = {"inline_keyboard": keyboard}
    
    if message_id:
        edit_message_text(text, message_id, reply_markup=reply_markup)
    else:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }
        requests.post(url, json=payload, timeout=10)

def handle_durum_callback(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    try:
        sched_conf = get_scheduler_config()
        interval_val = sched_conf["interval_minutes"]
        last_run_val = sched_conf["last_run_time"]
        is_running_val = sched_conf["is_running"]
        is_active_val = sched_conf.get("is_active", True)
        
        # Otonom temizlik durumunu alalım
        cleanup_conf = get_cleanup_config()
        cleanup_active = cleanup_conf.get("is_active", True)
        cleanup_interval = cleanup_conf.get("interval_hours", 24)
        cleanup_last = cleanup_conf.get("last_cleanup_time", 0.0)
        
        elapsed_min = (time.time() - last_run_val) / 60.0
        next_run_min = max(0.0, interval_val - elapsed_min)
        
        from datetime import timezone
        tr_tz = timezone(timedelta(hours=3))
        last_run_str = datetime.fromtimestamp(last_run_val, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S")
        next_run_str = (datetime.now(tr_tz) + timedelta(minutes=next_run_min)).strftime("%d.%m.%Y %H:%M:%S")
        cleanup_last_str = datetime.fromtimestamp(cleanup_last, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S") if cleanup_last > 0 else "Hiç çalıştırılmadı"
        
        status_msg = (
            "📊 <b>Sistem Durum Raporu (Bulut Entegreli)</b>\n\n"
            "📡 <b>RSS TARAYICI VE YAZICI:</b>\n"
            f"• <b>Otonom Tarayıcı:</b> {'🟢 Aktif' if is_active_val else '🔴 Pasif'}\n"
            f"• <b>Çalışma Durumu:</b> {'⚡ Tarama Yapılıyor...' if is_running_val else '💤 Beklemede'}\n"
            f"• <b>Tarama Sıklığı:</b> {interval_val} dakikada bir\n"
            f"• <b>Son Tarama Zamanı:</b> {last_run_str}\n"
            f"• <b>Sonraki Tarama:</b> {next_run_str} (~{int(next_run_min)} dakika sonra)\n\n"
            "🧹 <b>OTONOM HABER TEMİZLİK SİSTEMİ:</b>\n"
            f"• <b>Oto Temizlik:</b> {'🟢 Aktif' if cleanup_active else '🔴 Pasif'}\n"
            f"• <b>Temizlik Periyodu:</b> {cleanup_interval} saatte bir\n"
            f"• <b>Son Temizlik Zamanı:</b> {cleanup_last_str}\n\n"
            f"📰 <b>Toplam Yayınlanan Haber:</b> {get_total_posts_count()} adet\n\n"
            f"🔗 <b>Canlı Site:</b> https://aihaberler.web.app"
        )
        
        keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
        edit_message_text(status_msg, message_id, reply_markup={"inline_keyboard": keyboard}, chat_id=chat_id)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Durum Getirme Hatası", f"Hata: {e}")

def send_frequency_menu(callback_query=None):
    text = (
        "⏱️ <b>Otomatik Tarama Sıklığı Ayarı</b>\n\n"
        "Bulut otonom zamanlayıcısının ne sıklıkla RSS kaynaklarını tarayıp haber yazacağını seçin:\n"
        "💡 <i>(Tavsiye edilen süre: 20 veya 30 dakikadır)</i>"
    )
    
    keyboard = [
        [
            {"text": "⏱️ 10 Dakika", "callback_data": "set_sure:10"},
            {"text": "⏱️ 20 Dakika", "callback_data": "set_sure:20"}
        ],
        [
            {"text": "⏱️ 30 Dakika", "callback_data": "set_sure:30"},
            {"text": "⏱️ 60 Dakika", "callback_data": "set_sure:60"}
        ],
        [
            {"text": "⏱️ 120 Dakika", "callback_data": "set_sure:120"},
            {"text": "⏱️ 240 Dakika", "callback_data": "set_sure:240"}
        ],
        [
            {"text": "🔙 GERİ DÖN", "callback_data": "menu:yardim"}
        ]
    ]
    
    reply_markup = {"inline_keyboard": keyboard}
    if callback_query:
        message_id = callback_query["message"]["message_id"]
        callback_id = callback_query["id"]
        edit_message_text(text, message_id, reply_markup=reply_markup)
        answer_callback_query(callback_id)
    else:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }
        requests.post(url, json=payload, timeout=10)

def handle_frequency_setting(callback_query, minutes):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        update_scheduler_config(interval_minutes=minutes)
        answer_callback_query(callback_id, f"Tarama sıklığı {minutes} dakika yapıldı!")
        
        success_text = (
            "✅ <b>Zamanlama Güncellendi!</b>\n\n"
            f"Otomatik otonom tarama periyodu başarıyla <b>{minutes} dakika</b> olarak ayarlandı.\n\n"
            "Zamanlayıcı bu yeni değere göre bulutta çalışmaya devam edecektir."
        )
        keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
        edit_message_text(success_text, message_id, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        send_error("Ayar Güncelleme Hatası", f"Hata: {e}")

def handle_otonom_switch(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        sched_conf = get_scheduler_config()
        is_active = sched_conf.get("is_active", True)
        
        status_text = "🟢 AKTİF (OTOMATİK ÇALIŞIYOR)" if is_active else "🔴 PASİF (DURDURULDU)"
        
        text = (
            "🟢🔴 <b>Otonom Sistem Yönetim Paneli</b>\n\n"
            f"🎯 <b>Mevcut Durum:</b> {status_text}\n\n"
            "──────────────────────────────\n"
            "📖 <b>Açıklayıcı Bilgi:</b>\n"
            "• <b>Otonom Sistem Aktif Olduğunda:</b> Yapay zeka yazarınız, ayarladığınız tarama sıklığına göre (Örn: 20-30 dakikada bir) otomatik olarak buluttan RSS kaynaklarını tarar, özgün haberler üretir ve sitenizi anında derleyip günceller.\n"
            "• <b>Otonom Sistem Pasif Olduğunda:</b> Otomatik tarama ve haber üretimi tamamen durdurulur (askıya alınır). Sistem tamamen sizin manuel tetiklemenizi bekler.\n"
            "──────────────────────────────\n\n"
            "Aşağıdaki butonları kullanarak otonom sistemi açabilir veya kapatabilirsiniz:"
        )
        
        keyboard = []
        if is_active:
            keyboard.append([{"text": "🔴 OTONOM SİSTEMİ KAPAT", "callback_data": "otonom_toggle:off"}])
        else:
            keyboard.append([{"text": "🟢 OTONOM SİSTEMİ AÇ", "callback_data": "otonom_toggle:on"}])
            
        keyboard.append([{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}])
        
        edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Otonom Panel Hatası", f"Hata: {e}")

def handle_otonom_toggle_execute(callback_query, set_to):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        is_active = (set_to == "on")
        update_scheduler_config(is_active=is_active)
        
        status_text = "AKTİF" if is_active else "PASİF"
        answer_callback_query(callback_id, f"Otonom durum {status_text} yapıldı!")
        
        success_text = (
            "🟢🔴 <b>Otonom Tarayıcı Durumu Güncellendi</b>\n\n"
            f"Bulut otonom zamanlayıcı durumunuz başarıyla <b>{status_text}</b> yapıldı.\n\n"
            f"Otomatik tarayıcı şu anda: {'🟢 ÇALIŞIYOR' if is_active else '🔴 DURDURULDU (BEKLEMEDE)'}"
        )
        
        keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
        edit_message_text(success_text, message_id, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        send_error("Otonom Geçiş Hatası", f"Hata: {e}")

def send_rss_management_menu(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        sources = get_rss_sources()
        
        if not sources:
            text = "ℹ️ Sistemde kayıtlı herhangi bir RSS kaynağı bulunamadı."
            keyboard = [
                [{"text": "⚙️ RSS Kaynaklarını Yönet", "callback_data": "rss_manage:main"}],
                [{"text": "🔙 GERİ DÖN", "callback_data": "menu:yardim"}]
            ]
        else:
            grouped = {}
            for src in sources:
                cat = src.get("category", "genel")
                if cat not in grouped:
                    grouped[cat] = []
                grouped[cat].append(src)
                
            text = "📋 <b>Kayıtlı RSS Kaynak Listesi</b>\n\n"
            for cat, items in grouped.items():
                cat_label = cat.upper().replace('-', ' ')
                text += f"🗂️ <b>{cat_label}</b>\n"
                for item in items:
                    text += f"• <b>{html.escape(item['name'])}</b>: <code>{html.escape(item['url'])}</code>\n"
                text += "\n"
                
            text += "RSS kaynaklarını eklemek, silmek ve kategorileri yönetmek için aşağıdaki yönetim butonunu kullanın:"
            
            keyboard = [
                [{"text": "⚙️ RSS Kaynaklarını Yönet", "callback_data": "rss_manage:main"}],
                [{"text": "🔙 GERİ DÖN", "callback_data": "menu:yardim"}]
            ]
            
        reply_markup = {"inline_keyboard": keyboard}
        edit_message_text(text, message_id, reply_markup=reply_markup)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("RSS Arayüz Hatası", f"Hata: {e}")

def handle_rss_category_menu(callback_query, category_val):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        sources = get_rss_sources()
        cat_sources = [s for s in sources if s.get("category") == category_val]
        
        text = f"🗂️ <b>{category_val.upper()} Kategorisi RSS Kaynakları:</b>\n\n"
        
        keyboard = []
        if not cat_sources:
            text += "Bu kategoride kayıtlı kaynak bulunamadı."
        else:
            text += "Silmek istediğiniz RSS kaynağının üstüne tıklayın:\n"
            for src in cat_sources:
                name = src["name"]
                keyboard.append([{"text": f"🗑️ {name}", "callback_data": f"rss_del:{name}"}])
                
        keyboard.append([{"text": "🔙 Geri Dön", "callback_data": "menu:rss"}])
        
        reply_markup = {"inline_keyboard": keyboard}
        edit_message_text(text, message_id, reply_markup=reply_markup)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("RSS Kategori Hatası", f"Hata: {e}")

def handle_rss_deletion(callback_query, source_name):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        success = delete_rss_source(source_name)
        if success:
            answer_callback_query(callback_id, f"{source_name} silindi!")
            escaped_src = html.escape(source_name)
            success_text = (
                "✅ <b>RSS Kaynağı Silindi!</b>\n\n"
                f"<b>Silinen Kaynak:</b> <code>{escaped_src}</code>\n\n"
                "Kaynak veri tabanından başarıyla temizlenmiştir."
            )
        else:
            success_text = f"⚠️ Hata: <code>{html.escape(source_name)}</code> bulunamadı veya silinemedi."
            
        keyboard = [[{"text": "🔙 Kaynak Listesine Dön", "callback_data": "menu:rss"}]]
        edit_message_text(success_text, message_id, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        send_error("RSS Silme Hatası", f"Hata: {e}")

def send_rss_manage_dashboard(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    text = (
        "⚙️ <b>RSS Kaynakları ve Kategori Yönetim Paneli</b>\n\n"
        "Aşağıdaki interaktif butonları kullanarak kaynaklarınızı ve kategorilerinizi yönetebilirsiniz:\n\n"
        "💡 <i>(Yeni bir kaynak eklerken doğrudan web sitesinin linkini yapıştırabilirsiniz. Yapay zeka beslemeyi otomatik olarak keşfedecektir!)</i>"
    )
    
    keyboard = [
        [
            {"text": "➕ Kaynak Ekle (Otomatik Keşif)", "callback_data": "rss_manage:add_src"},
            {"text": "🗑️ Kaynak Sil", "callback_data": "rss_manage:del_src"}
        ],
        [
            {"text": "📂 Kategori Ekle", "callback_data": "rss_manage:add_cat"},
            {"text": "🗑️ Kategori Sil", "callback_data": "rss_manage:del_cat"}
        ],
        [
            {"text": "🔙 Kaynak Listesine Dön", "callback_data": "menu:rss"}
        ]
    ]
    
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id)

def handle_rss_add_src_callback(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    db = init_firebase()
    db.collection("system_config").document("bot_state").set({
        "state": "waiting_for:rss_url",
        "chat_id": str(callback_query["message"]["chat"]["id"])
    })
    
    text = (
        "🔗 <b>Lütfen eklemek istediğiniz sitenin veya RSS beslemesinin adresini gönderin:</b>\n\n"
        "💡 <i>Örnek: <code>trtspor.com.tr</code>, <code>https://webtekno.com</code> veya doğrudan <code>https://webtekno.com/rss.xml</code> gönderebilirsiniz.\n\n"
        "⚡ <b>NOT:</b> Başına <code>https://</code> yazmanıza gerek yoktur, sistem otomatik olarak tamamlayacaktır! Yapay zeka besleme adresini otomatik keşfedecektir!</i>"
    )
    
    keyboard = [[{"text": "❌ İPTAL ET", "callback_data": "rss_manage:cancel"}]]
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id)

def handle_rss_add_cat_callback(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    db = init_firebase()
    db.collection("system_config").document("bot_state").set({
        "state": "waiting_for:category_name",
        "chat_id": str(callback_query["message"]["chat"]["id"])
    })
    
    text = (
        "📂 <b>Lütfen eklemek istediğiniz yeni kategorinin adını yazın:</b>\n\n"
        "💡 <i>Örnek: <code>bilim</code>, <code>spor</code>, <code>ekonomi</code> gibi. Türkçe karakter kullanabilirsiniz.</i>"
    )
    
    keyboard = [[{"text": "❌ İPTAL ET", "callback_data": "rss_manage:cancel"}]]
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id)

def handle_rss_del_cat_menu(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    cats = get_categories()
    
    text = "🗑️ <b>Silmek istediğiniz kategoriyi seçin:</b>\n\n💡 <i>(Sadece içinde kayıtlı RSS kaynağı bulunmayan boş kategoriler silinebilir!)</i>"
    
    keyboard = []
    for cat in cats:
        cat_label = cat.capitalize().replace('-', ' ')
        keyboard.append([{"text": f"📂 {cat_label}", "callback_data": f"del_cat_confirm:{cat}"}])
        
    keyboard.append([{"text": "🔙 Geri Dön", "callback_data": "rss_manage:main"}])
    
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id)

def handle_del_cat_confirm(callback_query, cat_slug):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    # Check if category has active RSS sources
    sources = get_rss_sources()
    cat_sources = [s for s in sources if s.get("category") == cat_slug]
    
    if cat_sources:
        text = (
            f"❌ <b>Kategori Silinemedi!</b>\n\n"
            f"<code>{cat_slug}</code> kategorisinde kayıtlı <b>{len(cat_sources)}</b> adet RSS kaynağı bulunmaktadır.\n\n"
            f"⚠️ Bir kategoriyi silebilmek için önce o kategorideki tüm RSS kaynaklarını silmelisiniz."
        )
        keyboard = [[{"text": "🔙 Kategori Listesine Dön", "callback_data": "rss_manage:del_cat"}]]
        edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
        answer_callback_query(callback_id, "Silme başarısız.")
        return
        
    # Standard protection: do not let them delete core 3 categories
    if cat_slug in ["teknoloji", "oyun", "dizi-film"]:
        text = (
            f"❌ <b>Kategori Silinemedi!</b>\n\n"
            f"<code>{cat_slug}</code> kategorisi sistemin temel (çekirdek) kategorilerinden biridir ve silinemez."
        )
        keyboard = [[{"text": "🔙 Kategori Listesine Dön", "callback_data": "rss_manage:del_cat"}]]
        edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
        answer_callback_query(callback_id, "Silme başarısız.")
        return
        
    success = delete_category(cat_slug)
    if success:
        text = (
            f"✅ <b>Kategori Silindi!</b>\n\n"
            f"<b>Silinen Kategori Kodu:</b> <code>{cat_slug}</code>\n\n"
            f"Kategori bulut veri tabanından başarıyla kaldırılmıştır."
        )
    else:
        text = f"⚠️ Hata: <code>{cat_slug}</code> kategorisi silinemedi veya bulunamadı."
        
    keyboard = [[{"text": "🔙 Kategori Listesine Dön", "callback_data": "rss_manage:del_cat"}]]
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id, "Kategori silindi.")

def handle_rss_del_src_menu(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    cats = get_categories()
    text = "🗑️ <b>Silmek istediğiniz kaynağın kategorisini seçin:</b>"
    
    keyboard = []
    for cat in cats:
        cat_label = cat.capitalize().replace('-', ' ')
        keyboard.append([{"text": f"📂 {cat_label}", "callback_data": f"rss_del_cat:{cat}"}])
        
    keyboard.append([{"text": "🔙 Geri Dön", "callback_data": "rss_manage:main"}])
    
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id)

def handle_rss_del_cat_sources(callback_query, cat_slug):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    sources = get_rss_sources()
    cat_sources = [s for s in sources if s.get("category") == cat_slug]
    
    text = f"🗂️ <b>{cat_slug.upper()} Kategorisi RSS Kaynakları:</b>\n\n"
    
    keyboard = []
    if not cat_sources:
        text += "Bu kategoride kayıtlı kaynak bulunamadı."
    else:
        text += "Silmek istediğiniz RSS kaynağının üstüne tıklayın:\n"
        for src in cat_sources:
            name = src["name"]
            keyboard.append([{"text": f"🗑️ {name}", "callback_data": f"rss_del_src:{name}"}])
            
    keyboard.append([{"text": "🔙 Geri Dön", "callback_data": "rss_manage:del_src"}])
    
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id)

def handle_rss_del_src_execute(callback_query, src_name):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    success = delete_rss_source(src_name)
    escaped_src = html.escape(src_name)
    if success:
        text = (
            "✅ <b>RSS Kaynağı Silindi!</b>\n\n"
            f"<b>Silinen Kaynak:</b> <code>{escaped_src}</code>\n\n"
            "Kaynak veri tabanından başarıyla temizlenmiştir."
        )
    else:
        text = f"⚠️ Hata: <code>{escaped_src}</code> bulunamadı veya silinemedi."
        
    keyboard = [[{"text": "🔙 Yönetim Paneline Dön", "callback_data": "rss_manage:main"}]]
    edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id, "Kaynak silindi.")

def handle_rss_add_cat_execute(callback_query, cat_slug):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    db = init_firebase()
    state_doc = db.collection("system_config").document("bot_state").get()
    
    if not state_doc.exists:
        edit_message_text("❌ Hata: Girdi zaman aşımına uğradı veya durum bulunamadı.", message_id)
        answer_callback_query(callback_id)
        return
        
    state_data = state_doc.to_dict()
    metadata = state_data.get("metadata", {})
    f_url = metadata.get("url")
    f_name = metadata.get("name")
    
    if not f_url or not f_name:
        edit_message_text("❌ Hata: Keşfedilen besleme verileri bulunamadı.", message_id)
        answer_callback_query(callback_id)
        return
        
    # Add source to Firestore
    add_rss_source(f_name, f_url, cat_slug)
    
    # Clear state
    db.collection("system_config").document("bot_state").delete()
    
    success_text = (
        "✅ <b>RSS Kaynağı Başarıyla Eklendi!</b>\n\n"
        f"<b>İsim:</b> {f_name}\n"
        f"<b>Kategori:</b> {cat_slug.upper()}\n"
        f"<b>Adres:</b> <code>{f_url}</code>\n\n"
        f"🚀 Kaynak veri tabanına başarıyla eklenmiştir. Otonom tarayıcı bu kaynaktan da haber yazmaya başlayacaktır!"
    )
    
    keyboard = [[{"text": "🔙 Yönetim Paneline Dön", "callback_data": "rss_manage:main"}]]
    edit_message_text(success_text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id, "Kaynak başarıyla eklendi!")

def send_date_selection_menu(callback_query=None):
    try:
        index_data = get_posts_index()
        posts = index_data.get("posts", {})
        
        dates = sorted(list(set(p["date"] for p in posts.values())), reverse=True)
        recent_dates = dates[:8]
        
        if not recent_dates:
            if callback_query:
                message_id = callback_query["message"]["message_id"]
                edit_message_text("ℹ️ Sitede silinecek herhangi bir haber bulunamadı.", message_id)
                answer_callback_query(callback_query["id"])
            else:
                send_message("ℹ️ Sitede silinecek herhangi bir haber bulunamadı.")
            return
            
        keyboard = []
        for d in recent_dates:
            keyboard.append([{"text": f"📅 {d}", "callback_data": f"date:{d}"}])
            
        keyboard.append([{"text": "🔙 ANA MENÜ", "callback_data": "menu:yardim"}])
        reply_markup = {"inline_keyboard": keyboard}
        
        text = "📅 <b>Silmek istediğiniz haberin yayınlandığı tarihi seçin:</b>"
        
        if callback_query:
            message_id = callback_query["message"]["message_id"]
            edit_message_text(text, message_id, reply_markup=reply_markup)
            answer_callback_query(callback_query["id"])
        else:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
            payload = {
                "chat_id": chat_id.strip(),
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": reply_markup
            }
            requests.post(url, json=payload, timeout=10)
    except Exception as e:
        send_error("Haber Silme Hatası", f"Tarih seçimi menüsü oluşturulurken hata: {e}")

def handle_date_callback(callback_query, date_val):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        index_data = get_posts_index()
        posts = index_data.get("posts", {})
        
        date_posts = [p for p in posts.values() if p["date"] == date_val]
        
        if not date_posts:
            answer_callback_query(callback_id, "Bu tarihte haber bulunamadı.")
            return
            
        categories = {}
        for p in date_posts:
            cat = p.get("category", "teknoloji").lower()
            categories[cat] = categories.get(cat, 0) + 1
            
        keyboard = []
        for cat, count in categories.items():
            icon = "💻" if "tekno" in cat else ("🎮" if "oyun" in cat else ("🎬" if "dizi" in cat else "📂"))
            cat_name = cat.capitalize().replace('-', ' ')
            keyboard.append([{"text": f"{icon} {cat_name} ({count})", "callback_data": f"cat:{date_val}:{cat}"}])
            
        keyboard.append([{"text": "🔙 Tarih Seçimine Dön", "callback_data": "menu:sil"}])
        
        reply_markup = {"inline_keyboard": keyboard}
        edit_message_text(
            f"📂 <b>{date_val} Tarihli Haber Kategorileri:</b>\n\nLütfen listelemek istediğiniz haber kategorisini seçin:",
            message_id,
            reply_markup=reply_markup
        )
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Kategori Yükleme Hatası", f"Hata: {e}")

def handle_category_callback(callback_query, date_val, category_val):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    try:
        index_data = get_posts_index()
        posts = index_data.get("posts", {})
        
        cat_posts = [(p_id, p) for p_id, p in posts.items() if p["date"] == date_val and p.get("category", "teknoloji").lower() == category_val.lower()]
        
        if not cat_posts:
            answer_callback_query(callback_id, "Bu kategoride haber bulunamadı.")
            return
            
        selected_ids = get_or_init_multi_delete_state(chat_id, "sil", {"date": date_val, "category": category_val})
        
        keyboard = []
        for p_id, p in cat_posts:
            title = p["title"]
            if len(title) > 35:
                title = title[:32] + "..."
            icon = "✅" if p_id in selected_ids else "⬜"
            keyboard.append([{"text": f"{icon} {title}", "callback_data": f"toggle:{p_id}"}])
            
        delete_btn_text = f"🗑️ Seçilenleri Sil ({len(selected_ids)} adet)" if selected_ids else "🗑️ Seçilenleri Sil"
        keyboard.append([{"text": delete_btn_text, "callback_data": "confirm_multi_del"}])
        keyboard.append([{"text": "🔙 Kategori Seçimine Dön", "callback_data": f"date:{date_val}"}])
        
        reply_markup = {"inline_keyboard": keyboard}
        cat_display = category_val.capitalize().replace('-', ' ')
        edit_message_text(
            f"📰 <b>{date_val} / {cat_display} Haberleri:</b>\n\nSilmek istediğiniz haberleri seçin:",
            message_id,
            reply_markup=reply_markup
        )
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Haber Yükleme Hatası", f"Hata: {e}")

def handle_select_callback(callback_query, p_id):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    try:
        index_data = get_posts_index()
        posts = index_data.get("posts", {})
        
        p = posts.get(p_id)
        if not p:
            answer_callback_query(callback_id, "Haber bilgisi bulunamadı.")
            return
            
        keyboard = [
            [
                {"text": "✅ EVET, SİL", "callback_data": f"confirm_del:{p_id}"},
                {"text": "❌ HAYIR, İPTAL", "callback_data": "cancel_del"}
            ]
        ]
        
        reply_markup = {"inline_keyboard": keyboard}
        escaped_title = html.escape(p['title'])
        confirm_msg = (
            "🔴 <b>Emin Misiniz?</b>\n\n"
            f"<b>Haber:</b> {escaped_title}\n"
            f"<b>Tarih:</b> {p['date']}\n"
            f"<b>Dosya:</b> <code>{p['slug']}</code>\n"
            f"<b>Kategori:</b> {p.get('category', 'teknoloji').upper()}\n"
            f"<b>Görsel:</b> {p['image']}\n\n"
            "Bu haberi ve kapak görselini buluttan kalıcı olarak silmek istediğinize emin misiniz?\n"
            "💡 <i>(Bu işlem geri alınamaz ve canlı sitenizden kaldırılır!)</i>"
        )
        
        edit_message_text(confirm_msg, message_id, reply_markup=reply_markup)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Onay Ekranı Hatası", f"Onay ekranı oluşturulurken hata: {e}")

def handle_cancel_callback(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    edit_message_text("❌ Haber silme işlemi iptal edildi ve güvenle sonlandırıldı.", message_id)
    answer_callback_query(callback_id, "İptal edildi.")

def execute_github_deletion(p_info):
    slug = p_info["slug"]
    image_url = p_info["image"]
    
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    
    headers = {
        "Authorization": f"Bearer {github_token.strip()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AIHABERLER-Bot"
    }
    
    # 1. Fetch Markdown SHA dynamically
    md_path = f"web-portal/src/content/blog/{slug}"
    md_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{md_path}"
    
    r_get_md = requests.get(md_url, headers=headers, timeout=10)
    if r_get_md.status_code != 200:
        raise Exception(f"Markdown dosyası SHA'sı alınamadı: {r_get_md.status_code} {r_get_md.text}")
        
    md_sha = r_get_md.json().get("sha")
    
    # Delete Markdown File
    md_payload = {
        "message": f"style: delete news post '{slug}' via Telegram Bot",
        "sha": md_sha
    }
    
    r_md = requests.delete(md_url, json=md_payload, headers=headers, timeout=15)
    if r_md.status_code != 200:
        raise Exception(f"Markdown silme hatası: {r_md.status_code} {r_md.text}")
        
    # 2. Delete Image File (if custom)
    if "/images/news/" in image_url:
        img_name = os.path.basename(image_url)
        img_path = f"web-portal/public/images/news/{img_name}"
        img_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{img_path}"
        
        r_get = requests.get(img_url, headers=headers, timeout=10)
        if r_get.status_code == 200:
            img_sha = r_get.json().get("sha")
            if img_sha:
                img_payload = {
                    "message": f"style: delete news image '{img_name}' via Telegram Bot",
                    "sha": img_sha
                }
                requests.delete(img_url, json=img_payload, headers=headers, timeout=15)

def handle_confirm_callback(callback_query, p_id):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    edit_message_text("⏳ <b>Haber buluttan siliniyor, lütfen bekleyin...</b>\n(Dosyalar kaldırılıyor ve canlı site yeniden derleniyor)", message_id)
    answer_callback_query(callback_id, "Silme başlatıldı.")
    
    try:
        index_data = get_posts_index()
        posts = index_data.get("posts", {})
        
        p = posts.get(p_id)
        if not p:
            edit_message_text("❌ Hata: Haber bilgisi güncel indeks içinde bulunamadı.", message_id)
            return
            
        execute_github_deletion(p)
        remove_posts_from_index_locally([p_id])
        
        # Trigger build and deployment workflow
        try:
            trigger_github_workflow()
        except Exception as trigger_err:
            print(f"Error triggering build workflow: {trigger_err}")
            
        escaped_title = html.escape(p['title'])
        success_msg = (
            "✅ <b>Haber Başarıyla Silindi!</b>\n\n"
            f"<b>Silinen Haber:</b> {escaped_title}\n"
            f"<b>Silinen Dosya:</b> <code>{p['slug']}</code>\n\n"
            "🚀 Haber ve görsel dosyaları buluttan (GitHub) başarıyla temizlendi.\n"
            "⚡ Canlı site otomatik olarak yeniden derlenip güncellenecektir (yaklaşık 1-2 dakika sürer)."
        )
        keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
        edit_message_text(success_msg, message_id, reply_markup={"inline_keyboard": keyboard})
        
    except Exception as e:
        edit_message_text(f"❌ Haber silinirken hata oluştu: <code>{e}</code>", message_id)

def handle_toggle_callback(callback_query, p_id):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    db = init_firebase()
    state_doc = db.collection("system_config").document("bot_state").get()
    
    if not state_doc.exists:
        answer_callback_query(callback_id, "Zaman aşımı! Lütfen tekrar menüyü açın.")
        return
        
    state_data = state_doc.to_dict()
    if state_data.get("state") != "multi_delete":
        answer_callback_query(callback_id, "Geçersiz işlem durumu.")
        return
        
    selected_ids = state_data.get("selected_ids", [])
    if p_id in selected_ids:
        selected_ids.remove(p_id)
        action = "Seçim kaldırıldı."
    else:
        selected_ids.append(p_id)
        action = "Seçildi."
        
    state_data["selected_ids"] = selected_ids
    db.collection("system_config").document("bot_state").set(state_data)
    
    answer_callback_query(callback_id, action)
    
    # Re-render screen
    context = state_data.get("context")
    if context == "benzer":
        handle_benzer_haber_callback(callback_query, is_toggle=True)
    elif context == "sil":
        metadata = state_data.get("metadata", {})
        date_val = metadata.get("date")
        category_val = metadata.get("category")
        handle_category_callback(callback_query, date_val, category_val)

def handle_confirm_multi_del(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    db = init_firebase()
    state_doc = db.collection("system_config").document("bot_state").get()
    
    if not state_doc.exists:
        answer_callback_query(callback_id, "Zaman aşımı! Lütfen tekrar menüyü açın.")
        return
        
    state_data = state_doc.to_dict()
    selected_ids = state_data.get("selected_ids", [])
    
    if not selected_ids:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{bot_token.strip()}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_id,
            "text": "⚠️ Lütfen önce silmek istediğiniz haberleri seçin!",
            "show_alert": True
        }
        requests.post(url, json=payload, timeout=10)
        return
        
    # Get details of selected posts
    index_data = get_posts_index()
    posts = index_data.get("posts", {})
    
    selected_posts = []
    titles_list_str = ""
    for p_id in selected_ids:
        p = posts.get(p_id)
        if p:
            selected_posts.append(p)
            titles_list_str += f"• <code>{p['date']}</code> - {html.escape(p['title'])}\n"
            
    confirm_text = (
        "🔴 <b>Çoklu Silme Onayı</b>\n\n"
        f"Aşağıdaki <b>{len(selected_posts)}</b> adet haberi ve kapak görsellerini buluttan kalıcı olarak silmek istediğinize emin misiniz?\n\n"
        f"{titles_list_str}\n"
        "💡 <i>(Bu işlem geri alınamaz ve canlı sitenizden kaldırılır!)</i>"
    )
    
    keyboard = [
        [
            {"text": "✅ EVET, HEPSİNİ SİL", "callback_data": "execute_multi_del"},
            {"text": "❌ HAYIR, İPTAL", "callback_data": "cancel_multi_del"}
        ]
    ]
    
    edit_message_text(confirm_text, message_id, reply_markup={"inline_keyboard": keyboard})
    answer_callback_query(callback_id)

def handle_cancel_multi_del(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    db = init_firebase()
    state_doc = db.collection("system_config").document("bot_state").get()
    
    if not state_doc.exists:
        send_professional_help_dashboard(message_id)
        answer_callback_query(callback_id)
        return
        
    state_data = state_doc.to_dict()
    context = state_data.get("context")
    
    if context == "benzer":
        handle_benzer_haber_callback(callback_query, is_toggle=True)
    elif context == "sil":
        metadata = state_data.get("metadata", {})
        date_val = metadata.get("date")
        category_val = metadata.get("category")
        handle_category_callback(callback_query, date_val, category_val)
    else:
        send_professional_help_dashboard(message_id)
        
    answer_callback_query(callback_id)

def handle_execute_multi_del(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    edit_message_text("⏳ <b>Haberler buluttan siliniyor, lütfen bekleyin...</b>\n(Dosyalar paralel olarak kaldırılıyor)", message_id)
    answer_callback_query(callback_id, "Silme işlemi başlatıldı.")
    
    try:
        db = init_firebase()
        state_doc = db.collection("system_config").document("bot_state").get()
        if not state_doc.exists:
            edit_message_text("❌ Hata: Girdi zaman aşımına uğradı veya durum bulunamadı.", message_id)
            return
            
        state_data = state_doc.to_dict()
        selected_ids = state_data.get("selected_ids", [])
        
        if not selected_ids:
            edit_message_text("❌ Hata: Seçilen haber bulunamadı.", message_id)
            return
            
        index_data = get_posts_index()
        posts = index_data.get("posts", {})
        
        success_deleted = []
        failed_deleted = []
        
        # Parallel Deletion of selected posts using ThreadPoolExecutor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for p_id in selected_ids:
                p = posts.get(p_id)
                if not p:
                    failed_deleted.append((p_id, "Haber indekste bulunamadı."))
                    continue
                futures[executor.submit(execute_github_deletion, p)] = (p_id, p)
                
            for future in concurrent.futures.as_completed(futures):
                p_id, p = futures[future]
                try:
                    future.result()
                    success_deleted.append(p)
                except Exception as github_err:
                    print(f"Error deleting post {p_id} ({p['slug']}) from GitHub: {github_err}")
                    failed_deleted.append((p_id, str(github_err)))
                    
        # Remove successfully deleted posts from Firestore posts_index document locally in-memory
        if success_deleted:
            success_ids = [p_id for p_id in selected_ids if p_id not in [f[0] for f in failed_deleted]]
            remove_posts_from_index_locally(success_ids)
            
            # Trigger build and deployment workflow
            try:
                trigger_github_workflow()
            except Exception as trigger_err:
                print(f"Error triggering build workflow: {trigger_err}")
            
        # Clear bot state
        db.collection("system_config").document("bot_state").delete()
        
        report_msg = ""
        if success_deleted:
            success_details = "\n".join([f"• {html.escape(p['title'])}" for p in success_deleted])
            report_msg += f"✅ <b>Silinen Haberler ({len(success_deleted)} adet):</b>\n{success_details}\n\n"
            
        if failed_deleted:
            failed_details = "\n".join([f"• <b>ID: {fid}</b>: {err}" for fid, err in failed_deleted])
            report_msg += f"❌ <b>Silinemeyen Haberler ({len(failed_deleted)} adet):</b>\n{failed_details}\n\n"
            
        if report_msg:
            report_msg += (
                "🚀 Başarıyla silinen haber dosyaları buluttan (GitHub) temizlendi.\n"
                "⚡ Canlı site otomatik olarak yeniden derlenip güncellenecektir (yaklaşık 1-2 dakika sürer)."
            )
            keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
            edit_message_text(report_msg, message_id, reply_markup={"inline_keyboard": keyboard})
        else:
            edit_message_text("❌ Hiçbir haber silinemedi.", message_id)
            
    except Exception as e:
        send_error("Çoklu Haber Silme Başarısız", f"Silme işlemi sırasında kritik hata: {e}")
        edit_message_text(f"❌ Haberler silinirken hata oluştu: <code>{e}</code>", message_id)

def handle_callback_query_routing(callback_query):
    data = callback_query.get("data", "")
    
    # 1. Main Dashboard routes
    if data == "menu:yardim":
        try:
            db = init_firebase()
            db.collection("system_config").document("bot_state").delete()
        except:
            pass
        send_professional_help_dashboard(callback_query["message"]["message_id"])
        answer_callback_query(callback_query["id"])
    elif data == "menu:durum":
        handle_durum_callback(callback_query)
    elif data == "menu:tara":
        trigger_github_workflow()
        answer_callback_query(callback_query["id"], "Bulut taraması tetiklendi!")
    elif data == "menu:sure":
        send_frequency_menu(callback_query)
    elif data.startswith("set_sure:"):
        mins = int(data.split(":", 1)[1])
        handle_frequency_setting(callback_query, mins)
    elif data == "menu:otonom":
        handle_otonom_switch(callback_query)
    elif data.startswith("otonom_toggle:"):
        set_to = data.split(":", 1)[1]
        handle_otonom_toggle_execute(callback_query, set_to)
    elif data == "menu:benzer":
        handle_benzer_haber_callback(callback_query)
    elif data == "menu:ototemizleme":
        handle_ototemizleme_menu(callback_query)
    elif data.startswith("ototemizlik_toggle:"):
        set_to = data.split(":", 1)[1]
        is_active = (set_to == "on")
        update_cleanup_config(is_active=is_active)
        answer_callback_query(callback_query["id"], f"🟢 Oto temizlik {'aktif' if is_active else 'pasif'} yapıldı!", show_alert=True)
        handle_ototemizleme_menu(callback_query)
    elif data.startswith("set_temizlik_sure:"):
        hours = int(data.split(":", 1)[1])
        update_cleanup_config(interval_hours=hours)
        answer_callback_query(callback_query["id"], f"⏱️ Temizlik periyodu {hours} saat yapıldı!", show_alert=True)
        handle_ototemizleme_menu(callback_query)
    elif data == "ototemizlik_manuel":
        success = trigger_github_cleanup_workflow()
        if success:
            answer_callback_query(callback_query["id"], "Manuel temizlik tetiklendi!")
            edit_message_text(
                "⚡ <b>Manuel Otonom Temizlik Tetiklendi!</b>\n\n"
                "GitHub Actions bulut sunucusu üzerinde otonom temizlik işlemi başarıyla başlatıldı.\n"
                "🔍 Son 24 saatlik haberler Gemma 4 31b ile analiz edilip aykırı/mükerrer içerikler temizlenecektir.\n\n"
                "📊 İşlem tamamlandığında detaylı rapor Telegram üzerinden size iletilecektir (yaklaşık 1-2 dakika sürer).",
                callback_query["message"]["message_id"],
                reply_markup={"inline_keyboard": [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]}
            )
        else:
            answer_callback_query(callback_query["id"], "Tetikleme başarısız oldu!")
    elif data == "menu:rss":
        send_rss_management_menu(callback_query)
    elif data == "rss_manage:main":
        send_rss_manage_dashboard(callback_query)
    elif data == "rss_manage:add_src":
        handle_rss_add_src_callback(callback_query)
    elif data == "rss_manage:add_cat":
        handle_rss_add_cat_callback(callback_query)
    elif data == "rss_manage:del_cat":
        handle_rss_del_cat_menu(callback_query)
    elif data == "rss_manage:del_src":
        handle_rss_del_src_menu(callback_query)
    elif data == "rss_manage:cancel":
        db = init_firebase()
        db.collection("system_config").document("bot_state").delete()
        send_rss_manage_dashboard(callback_query)
    elif data.startswith("rss_del_cat:"):
        cat_slug = data.split(":", 1)[1]
        handle_rss_del_cat_sources(callback_query, cat_slug)
    elif data.startswith("rss_del_src:"):
        src_name = data.split(":", 1)[1]
        handle_rss_del_src_execute(callback_query, src_name)
    elif data.startswith("del_cat_confirm:"):
        cat_slug = data.split(":", 1)[1]
        handle_del_cat_confirm(callback_query, cat_slug)
    elif data.startswith("add_rss_cat:"):
        cat_slug = data.split(":", 1)[1]
        handle_rss_add_cat_execute(callback_query, cat_slug)
    elif data == "menu:sil":
        send_date_selection_menu(callback_query)
        
    # 2. Interactive delete routes
    elif data.startswith("date:"):
        date_val = data.split(":", 1)[1]
        handle_date_callback(callback_query, date_val)
    elif data.startswith("cat:"):
        parts = data.split(":", 2)
        date_val = parts[1]
        cat_val = parts[2]
        handle_category_callback(callback_query, date_val, cat_val)
    elif data.startswith("sel:"):
        p_id = data.split(":", 1)[1]
        handle_select_callback(callback_query, p_id)
    elif data == "cancel_del":
        handle_cancel_callback(callback_query)
    elif data.startswith("confirm_del:"):
        p_id = data.split(":", 1)[1]
        handle_confirm_callback(callback_query, p_id)
    elif data.startswith("toggle:"):
        p_id = data.split(":", 1)[1]
        handle_toggle_callback(callback_query, p_id)
    elif data == "confirm_multi_del":
        handle_confirm_multi_del(callback_query)
    elif data == "execute_multi_del":
        handle_execute_multi_del(callback_query)
    elif data == "cancel_multi_del":
        handle_cancel_multi_del(callback_query)

def add_custom_request(topic):

    """Adds a custom news request to the Firestore queue."""
    db = init_firebase()
    doc_ref = db.collection("custom_requests").document()
    doc_ref.set({
        "topic": topic,
        "status": "pending",
        "requested_at": time.time()
    })
    return True

# GITHUB API REAL-TIME METADATA
def get_total_posts_count():
    """Fetches the real-time count of markdown posts from the GitHub repository."""
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    path = "web-portal/src/content/blog"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AIHABERLER-Bot"
    }
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token.strip()}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            files = r.json()
            return len([f for f in files if f.get("name", "").endswith(".md")])
    except Exception as e:
        print(f"Hata: GitHub dosya listesi alınamadı: {e}")
    return 0

# TELEGRAM DISPATCHER
def send_message(text):
    """Sends a Telegram message."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram mesaj gönderme hatası: {e}")

def send_success(title, message):
    text = f"💚 <b>{title}</b>\n\n{message}"
    send_message(text)

def send_error(title, message):
    text = f"💔 <b>{title}</b>\n\n{message}"
    send_message(text)

# GITHUB WORKFLOW TRIGGER
def trigger_github_workflow():
    """Triggers GitHub Actions workflow via dispatch API or falls back to Firestore trigger."""
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    workflow_id = "autonomous_rss.yml"
    
    # 1. Firestore Meşguliyet Kontrolü (Otonom / Manuel Çakışma Önleme)
    try:
        sched_conf = get_scheduler_config()
        if sched_conf.get("is_running", False):
            send_message(
                "⚠️ <b>Aktif Tarama Zaten Devam Ediyor!</b>\n\n"
                "Sistem şu anda otonom veya manuel olarak tetiklenmiş bir tarama işlemi yürütmektedir.\n\n"
                "🚫 <b>Çakışma Koruması:</b> Aynı anda birden fazla tarama yapılması, haberlerin mükerrer yazılmasına veya sunucu hatalarına yol açabileceği için şu an tetikleme yapılamaz.\n\n"
                "⏳ <i>Lütfen mevcut işlemin bitmesini (yaklaşık 1-2 dakika) bekleyin.</i>"
            )
            return False
    except Exception as sched_err:
        print(f"Scheduler checking error: {sched_err}")
        
    # 2. GitHub Actions Canlı Meşguliyet Kontrolü (Mükerrer Tetikleme Önleme)
    if github_token:
        try:
            check_headers = {
                "Authorization": f"Bearer {github_token.strip()}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "AIHABERLER-Bot"
            }
            
            # in_progress ve queued durumdaki aktif işleri sorgula
            r_prog = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?status=in_progress",
                headers=check_headers,
                timeout=10
            )
            r_queue = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?status=queued",
                headers=check_headers,
                timeout=10
            )
            
            active_runs = 0
            if r_prog.status_code == 200:
                active_runs += len(r_prog.json().get("workflow_runs", []))
            if r_queue.status_code == 200:
                active_runs += len(r_queue.json().get("workflow_runs", []))
                
            if active_runs > 0:
                send_message(
                    "⚠️ <b>Bulut Sunucusu Şu Anda Meşgul!</b>\n\n"
                    "Bulut sunucumuz (GitHub Actions) üzerinde şu anda aktif veya sırada bekleyen bir tarama/derleme işi çalışmaktadır.\n\n"
                    "🚫 <b>Güvenlik Duvarı Engeli:</b> Mükerrer veri kaydını ve derleme hatalarını önlemek amacıyla, aktif bulut işlemi bitmeden yeni bir tarama başlatılamaz.\n\n"
                    "⏳ <i>Lütfen mevcut bulut derlemesinin tamamlanmasını (yaklaşık 1-2 dakika) bekleyin.</i>"
                )
                return False
        except Exception as check_err:
            print(f"GitHub workflow active runs checking error: {check_err}")
            
    send_message("🔄 <b>Manuel tarama isteği alındı.</b> Bulut sunucusu (GitHub Actions) ile bağlantı kuruluyor...")
    
    if not github_token:
        # Fallback to scheduling
        try:
            update_scheduler_config(last_run_time=0, is_running=False)
            send_success(
                "Tarama Sıraya Eklendi (Bulut Zamanlayıcı)",
                "GitHub erişim anahtarı (<code>GITHUB_PAT</code>) yapılandırılmadığı için işlem bulut zamanlayıcısına (Cron) havale edildi.\n\n"
                "⚡ <b>Bulut Yazarı</b> en geç <b>10 dakika içinde</b> otomatik olarak uyanacak, taramayı yapacak ve yeni haberleri yayınlayacaktır.\n\n"
                "💡 <i>Öneri: Vercel panelinden <code>GITHUB_PAT</code> anahtarını tanımlayarak <b>/tara</b> komutunun anında (1 saniyede) tetiklenmesini sağlayabilirsiniz!</i>"
            )
        except Exception as e:
            send_error("Manuel Tarama Hatası", f"Firestore zamanlayıcı tetiklenirken hata oluştu: {e}")
        return False
        
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"Bearer {github_token.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AIHABERLER-Bot"
    }
    data = {
        "ref": "main",
        "inputs": {
            "force": "true"
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 204:
            send_success(
                "Bulut Taraması Tetiklendi!",
                "🚀 <b>GitHub Actions Bulut Sunucusu ANINDA tetiklendi!</b>\n\n"
                "Yapay zeka yazarımız bulutta RSS kaynaklarını taramaya ve makaleleri yazmaya başladı.\n"
                "👉 İşlem tamamlandığında (yaklaşık 2-3 dakika) yeni haberlerin tıklanabilir linklerini içeren başarı raporu doğrudan buraya iletilecektir."
            )
            return True
        else:
            err_detail = response.text
            print(f"HATA: GitHub API yanıt kodu: {response.status_code}. Detay: {err_detail}")
            update_scheduler_config(last_run_time=0, is_running=False)
            send_success(
                "Tarama Sıraya Eklendi (API Hatası Sonrası Fallback)",
                f"GitHub API ile bağlantıda sorun yaşandı (Kod: {response.status_code}). Güvenli yedekleme planı devreye sokuldu ve tarama Firestore bulut kuyruğuna eklendi.\n\n"
                "⚡ En geç <b>10 dakika içinde</b> otomatik tarama başlayacaktır."
            )
            return False
    except Exception as e:
        print(f"HATA: GitHub workflow tetiklenirken hata oluştu: {e}")
        update_scheduler_config(last_run_time=0, is_running=False)
        send_success(
            "Tarama Sıraya Eklendi (Bağlantı Hatası Sonrası Fallback)",
            f"Bağlantı hatası oluştu: {e}\nİşlem güvenli bir şekilde bulut zamanlayıcısına havale edildi. En geç <b>10 dakika içinde</b> otomatik olarak çalışacaktır."
        )
        return False

def trigger_github_cleanup_workflow():
    """Triggers GitHub Actions workflow with cleanup input parameter."""
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    workflow_id = "autonomous_rss.yml"
    
    # Check Firestore status or GitHub Actions workflow status just like in trigger_github_workflow
    try:
        sched_conf = get_scheduler_config()
        if sched_conf.get("is_running", False):
            send_message(
                "⚠️ <b>Aktif İşlem Zaten Devam Ediyor!</b>\n\n"
                "Sistem şu anda otonom veya manuel olarak tetiklenmiş bir tarama/temizlik işlemi yürütmektedir.\n\n"
                "⏳ <i>Lütfen mevcut işlemin bitmesini bekleyin.</i>"
            )
            return False
    except Exception as sched_err:
        print(f"Scheduler checking error: {sched_err}")
        
    if github_token:
        try:
            check_headers = {
                "Authorization": f"Bearer {github_token.strip()}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "AIHABERLER-Bot"
            }
            r_prog = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?status=in_progress",
                headers=check_headers,
                timeout=10
            )
            r_queue = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?status=queued",
                headers=check_headers,
                timeout=10
            )
            active_runs = 0
            if r_prog.status_code == 200:
                active_runs += len(r_prog.json().get("workflow_runs", []))
            if r_queue.status_code == 200:
                active_runs += len(r_queue.json().get("workflow_runs", []))
                
            if active_runs > 0:
                send_message(
                    "⚠️ <b>Bulut Sunucusu Şu Anda Meşgul!</b>\n\n"
                    "Bulut sunucumuz (GitHub Actions) üzerinde şu anda aktif veya sırada bekleyen bir tarama/derleme işi çalışmaktadır.\n\n"
                    "⏳ <i>Lütfen mevcut bulut işleminin tamamlanmasını bekleyin.</i>"
                )
                return False
        except Exception as check_err:
            print(f"GitHub workflow active runs checking error: {check_err}")
            
    if not github_token:
        send_error("Manuel Temizlik Hatası", "GitHub Actions API anahtarı (<code>GITHUB_PAT</code>) tanımlanmadığı için manuel temizlik anında başlatılamıyor. Lütfen /yardim menüsünden otonom temizliği aktif bırakın.")
        return False
        
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"Bearer {github_token.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AIHABERLER-Bot"
    }
    data = {
        "ref": "main",
        "inputs": {
            "cleanup": "true"
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 204:
            return True
        else:
            print(f"HATA: GitHub API yanıt kodu: {response.status_code}. Detay: {response.text}")
            send_error("Manuel Temizlik Hatası", f"GitHub API dispatch hatası: {response.status_code}")
            return False
    except Exception as e:
        print(f"HATA: GitHub workflow tetiklenirken hata oluştu: {e}")
        send_error("Manuel Temizlik Hatası", f"Bağlantı hatası: {e}")
        return False

def handle_ototemizleme_menu(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    try:
        config = get_cleanup_config()
        is_active = config.get("is_active", True)
        interval_hours = config.get("interval_hours", 24)
        last_cleanup = config.get("last_cleanup_time", 0.0)
        
        status_text = "🟢 AKTİF (OTOMATİK ÇALIŞIYOR)" if is_active else "🔴 PASİF (DURDURULDU)"
        
        from datetime import timezone
        tr_tz = timezone(timedelta(hours=3))
        if last_cleanup > 0:
            last_cleanup_str = datetime.fromtimestamp(last_cleanup, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S")
        else:
            last_cleanup_str = "Hiç çalıştırılmadı"
            
        text = (
            "🧹 <b>Otonom Haber Temizlik Paneli</b> 🧹\n"
            "──────────────────────────────\n"
            f"🎯 <b>Mevcut Durum:</b> {status_text}\n"
            f"⏱️ <b>Kontrol Periyodu:</b> Her {interval_hours} saatte bir\n"
            f"📅 <b>Son Temizlik Zamanı:</b> {last_cleanup_str}\n\n"
            "──────────────────────────────\n"
            "📖 <b>Açıklayıcı Bilgi:</b>\n"
            "• Bu sistem, belirlediğiniz periyot dolduğunda <b>son 24 saatte yayınlanan haberleri</b> otomatik olarak tarar.\n"
            "• <b>Gemma 4 31b</b> yapay zeka modeli ile yayın politikasına aykırı veya mükerrer (kopya) olan içerikleri tespit eder, siler ve canlı sitenizi günceller.\n"
            "──────────────────────────────\n\n"
            "Aşağıdaki butonları kullanarak otonom temizlik durumunu açıp kapatabilir veya periyodu değiştirebilirsiniz:"
        )
        
        keyboard = [
            [
                {"text": f"{'🔴 Kapat (Devre Dışı Bırak)' if is_active else '🟢 Aktifleştir (Çalıştır)'}", "callback_data": f"ototemizlik_toggle:{'off' if is_active else 'on'}"}
            ],
            [
                {"text": "⏱️ 12 Saat", "callback_data": "set_temizlik_sure:12"},
                {"text": "⏱️ 24 Saat", "callback_data": "set_temizlik_sure:24"}
            ],
            [
                {"text": "⏱️ 48 Saat", "callback_data": "set_temizlik_sure:48"},
                {"text": "⏱️ 72 Saat", "callback_data": "set_temizlik_sure:72"}
            ],
            [
                {"text": "⚡ Şimdi Temizle (Manuel)", "callback_data": "ototemizlik_manuel"},
                {"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}
            ]
        ]
        
        edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard}, chat_id=chat_id)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Oto Temizlik Panel Hatası", f"Hata: {e}")

def send_ototemizleme_menu_message():
    try:
        config = get_cleanup_config()
        is_active = config.get("is_active", True)
        interval_hours = config.get("interval_hours", 24)
        last_cleanup = config.get("last_cleanup_time", 0.0)
        
        status_text = "🟢 AKTİF (OTOMATİK ÇALIŞIYOR)" if is_active else "🔴 PASİF (DURDURULDU)"
        
        from datetime import timezone
        tr_tz = timezone(timedelta(hours=3))
        if last_cleanup > 0:
            last_cleanup_str = datetime.fromtimestamp(last_cleanup, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S")
        else:
            last_cleanup_str = "Hiç çalıştırılmadı"
            
        text = (
            "🧹 <b>Otonom Haber Temizlik Paneli</b> 🧹\n"
            "──────────────────────────────\n"
            f"🎯 <b>Mevcut Durum:</b> {status_text}\n"
            f"⏱️ <b>Kontrol Periyodu:</b> Her {interval_hours} saatte bir\n"
            f"📅 <b>Son Temizlik Zamanı:</b> {last_cleanup_str}\n\n"
            "──────────────────────────────\n"
            "📖 <b>Açıklayıcı Bilgi:</b>\n"
            "• Bu sistem, belirlediğiniz periyot dolduğunda <b>son 24 saatte yayınlanan haberleri</b> otomatik olarak tarar.\n"
            "• <b>Gemma 4 31b</b> yapay zeka modeli ile yayın politikasına aykırı veya mükerrer (kopya) olan içerikleri tespit eder, siler ve canlı sitenizi günceller.\n"
            "──────────────────────────────\n\n"
            "Aşağıdaki butonları kullanarak otonom temizlik durumunu açıp kapatabilir veya periyodu değiştirebilirsiniz:"
        )
        
        keyboard = [
            [
                {"text": f"{'🔴 Kapat (Devre Dışı Bırak)' if is_active else '🟢 Aktifleştir (Çalıştır)'}", "callback_data": f"ototemizlik_toggle:{'off' if is_active else 'on'}"}
            ],
            [
                {"text": "⏱️ 12 Saat", "callback_data": "set_temizlik_sure:12"},
                {"text": "⏱️ 24 Saat", "callback_data": "set_temizlik_sure:24"}
            ],
            [
                {"text": "⏱️ 48 Saat", "callback_data": "set_temizlik_sure:48"},
                {"text": "⏱️ 72 Saat", "callback_data": "set_temizlik_sure:72"}
            ],
            [
                {"text": "⚡ Şimdi Temizle (Manuel)", "callback_data": "ototemizlik_manuel"},
                {"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}
            ]
        ]
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": keyboard}
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending ototemizleme menu: {e}")

# VERCEL SERVERLESS HANDLER
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Processes incoming Telegram Webhook post requests."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
        except Exception as parse_err:
            self.wfile.write(json.dumps({"status": "invalid json", "error": str(parse_err)}).encode())
            return
            
        # 1. Callback Query intercept
        callback_query = update.get("callback_query")
        if callback_query:
            from_user = callback_query.get("from", {})
            user_id = str(from_user.get("id", ""))
            allowed_chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if not allowed_chat_id or user_id != allowed_chat_id.strip():
                print(f"Yetkisiz callback kullanıcısı engellendi: {user_id}")
                self.wfile.write(json.dumps({"status": "unauthorized"}).encode())
                return
                
            try:
                handle_callback_query_routing(callback_query)
            except Exception as cb_err:
                print(f"Error handling callback query: {cb_err}")
            self.wfile.write(json.dumps({"status": "processed"}).encode())
            return
            
        message = update.get("message")
        if not message:
            self.wfile.write(json.dumps({"status": "no message"}).encode())
            return
            
        from_user = message.get("from", {})
        user_id = str(from_user.get("id", ""))
        text = message.get("text", "").strip()
        
        allowed_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not allowed_chat_id or user_id != allowed_chat_id.strip():
            print(f"Yetkisiz kullanıcı engellendi: {user_id}")
            self.wfile.write(json.dumps({"status": "unauthorized"}).encode())
            return
            
        if not text:
            self.wfile.write(json.dumps({"status": "no text"}).encode())
            return
            
        try:
            # CHECK BOT INPUT STATE MACHINE
            db = init_firebase()
            state_doc = db.collection("system_config").document("bot_state").get()
            user_state = {}
            if state_doc.exists:
                user_state = state_doc.to_dict()
            
            active_state = user_state.get("state")
            is_command = text.startswith("/")
            
            if active_state and not is_command:
                if active_state == "waiting_for:rss_url":
                    url_val = text.strip()
                    if not url_val.startswith(("http://", "https://")):
                        url_val = "https://" + url_val
                        
                    send_message(f"🔄 <code>{url_val}</code> adresi inceleniyor ve RSS beslemesi aranıyor...")
                    
                    is_valid_direct, direct_title = verify_and_parse_feed(url_val)
                    discovered_feeds = []
                    if is_valid_direct:
                        discovered_feeds.append((direct_title, url_val))
                    else:
                        discovered_feeds = discover_rss_feed(url_val)
                        
                    if discovered_feeds:
                        f_title, f_url = discovered_feeds[0]
                        
                        db.collection("system_config").document("bot_state").set({
                            "state": "waiting_for:rss_category",
                            "metadata": {
                                "url": f_url,
                                "name": f_title
                            }
                        })
                        
                        cats = get_categories()
                        keyboard = []
                        for cat in cats:
                            cat_label = cat.capitalize().replace('-', ' ')
                            keyboard.append([{"text": f"📂 {cat_label}", "callback_data": f"add_rss_cat:{cat}"}])
                        keyboard.append([{"text": "❌ İPTAL ET", "callback_data": "rss_manage:cancel"}])
                        
                        reply_markup = {"inline_keyboard": keyboard}
                        confirm_msg = (
                            "🔍 <b>RSS Beslemesi Keşfedildi!</b>\n\n"
                            f"📋 <b>Kaynak Adı:</b> {f_title}\n"
                            f"🔗 <b>Kaynak Adresi:</b> <code>{f_url}</code>\n\n"
                            "📂 <b>Lütfen bu kaynağın ekleneceği kategoriyi seçin:</b>"
                        )
                        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                        chat_id = os.getenv("TELEGRAM_CHAT_ID")
                        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
                        requests.post(url, json={
                            "chat_id": chat_id.strip(),
                            "text": confirm_msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup
                        }, timeout=10)
                    else:
                        db.collection("system_config").document("bot_state").delete()
                        send_message(
                            "❌ <b>RSS Keşfi Başarısız!</b>\n\n"
                            f"Girdiğiniz adreste (<code>{url_val}</code>) geçerli bir XML/RSS beslemesi otomatik olarak bulunamadı.\n\n"
                            "💡 <i>Lütfen doğrudan geçerli bir RSS linki girdiğinizden emin olun veya /yardim panelinden tekrar deneyin.</i>"
                        )
                    self.wfile.write(json.dumps({"status": "processed"}).encode())
                    return
                    
                elif active_state == "waiting_for:category_name":
                    cat_name = text.strip()
                    success, cat_slug = add_category(cat_name)
                    db.collection("system_config").document("bot_state").delete()
                    
                    if success:
                        send_success(
                            "Kategori Başarıyla Eklendi!",
                            f"📂 <b>Kategori Adı:</b> {cat_name}\n"
                            f"🏷️ <b>Kategori Kodu:</b> <code>{cat_slug}</code>\n\n"
                            "🚀 Yeni kategori başarıyla bulut veri tabanına kaydedilmiştir.\n"
                            "⚡ Bu kategoriye bağlı en az 1 haber yayınlandığı anda sitenizin menüsünde dinamik olarak belirecektir!"
                        )
                    else:
                        send_message(
                            f"⚠️ <b>Kategori Zaten Mevcut!</b>\n\n"
                            f"<code>{cat_slug}</code> kodlu kategori veri tabanında zaten kayıtlıdır."
                        )
                    self.wfile.write(json.dumps({"status": "processed"}).encode())
                    return
            if text in ["/help", "/yardim", "/yardım", "/start"]:
                send_professional_help_dashboard()
                
            elif text in ["/ototemizlik", "/ototemizleme"]:
                send_ototemizleme_menu_message()
                
            elif text == "/sil":
                send_date_selection_menu()
                
            elif text == "/durum":
                try:
                    sched_conf = get_scheduler_config()
                    interval_val = sched_conf["interval_minutes"]
                    last_run_val = sched_conf["last_run_time"]
                    is_running_val = sched_conf["is_running"]
                    is_active_val = sched_conf.get("is_active", True)
                    
                    elapsed_min = (time.time() - last_run_val) / 60.0
                    next_run_min = max(0.0, interval_val - elapsed_min)
                    
                    from datetime import timezone
                    tr_tz = timezone(timedelta(hours=3))
                    last_run_str = datetime.fromtimestamp(last_run_val, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S")
                    next_run_str = (datetime.now(tr_tz) + timedelta(minutes=next_run_min)).strftime("%d.%m.%Y %H:%M:%S")
                    
                    status_msg = (
                        "📊 <b>Sistem Durum Raporu (Bulut Entegreli)</b>\n\n"
                        f"🟢 <b>Otonom Tarayıcı:</b> {'Aktif (Otomatik Çalışıyor)' if is_active_val else 'Durduruldu (Askıya Alındı)'}\n"
                        f"⚡ <b>Çalışma Durumu:</b> {'Tarama Yapılıyor...' if is_running_val else 'Beklemede'}\n"
                        f"⏱️ <b>Tarama Sıklığı:</b> Her {interval_val} dakikada bir\n"
                        f"📅 <b>Son Tarama Zamanı:</b> {last_run_str}\n"
                        f"⏳ <b>Sonraki Tarama:</b> {next_run_str} (~{int(next_run_min)} dakika sonra)\n"
                        f"📰 <b>Toplam Yayınlanan Haber:</b> {get_total_posts_count()} adet\n\n"
                        f"🔗 <b>Canlı Site:</b> https://aihaberler.web.app"
                    )
                    send_message(status_msg)
                except Exception as e:
                    send_message(f"⚠️ Durum bilgisi alınamadı: {e}")
                    
            elif text == "/tara":
                trigger_github_workflow()
                
            elif text in ["/sure", "/süre"] or text.startswith("/sure ") or text.startswith("/süre "):
                send_frequency_menu()
                    
            elif text in ["/baslat", "/başlat"]:
                try:
                    update_scheduler_config(is_active=True)
                    sched_conf = get_scheduler_config()
                    interval_val = sched_conf["interval_minutes"]
                    send_success(
                        "Otonom Zamanlayıcı Başlatıldı!",
                        f"Otomatik tarayıcımız başarıyla <b>BAŞLATILDI (AKTİFLEŞTİRİLDİ)</b>.\n\n"
                        f"Bulut zamanlayıcı her <b>{interval_val} dakikada bir</b> otomatik olarak taranıp haber yayınlamaya devam edecektir."
                    )
                except Exception as e:
                    send_message(f"⚠️ Hata: Zamanlayıcı başlatılamadı: {e}")
                    
            elif text == "/durdur":
                try:
                    update_scheduler_config(is_active=False)
                    send_success(
                        "Otonom Zamanlayıcı Durduruldu!",
                        f"Otomatik tarayıcımız başarıyla <b>DURDURULDU (ASKIYA ALINDI)</b>.\n\n"
                        f"Arka plan otomatik taramaları askıya alınmıştır. Ancak özel haber talepleriniz veya manuel <b>/tara</b> tetiklemeleriniz kesintisiz çalışmaya devam eder."
                    )
                except Exception as e:
                    send_message(f"⚠️ Hata: Zamanlayıcı durdurulamadı: {e}")
                    
            elif text == "/rss_liste":
                try:
                    sources = get_rss_sources()
                    if not sources:
                        send_message("ℹ️ Kayıtlı RSS kaynağı bulunamadı.")
                    else:
                        grouped = {}
                        for src in sources:
                            cat = src.get("category", "genel")
                            if cat not in grouped:
                                grouped[cat] = []
                            grouped[cat].append(src)
                            
                        msg = "📋 <b>Kayıtlı RSS Kaynakları (Firestore)</b>\n\n"
                        for cat, items in grouped.items():
                            msg += f"🗂️ <b>{cat.upper()}</b>\n"
                            for item in items:
                                msg += f"• <b>{html.escape(item['name'])}</b>: <code>{html.escape(item['url'])}</code>\n"
                            msg += "\n"
                        send_message(msg)
                except Exception as e:
                    send_message(f"⚠️ RSS listesi alınırken hata oluştu: {e}")
                    
            elif text.startswith("/rss_ekle"):
                try:
                    parts = text.split(maxsplit=3)
                    if len(parts) < 4:
                        send_message("⚠️ Eksik parametre! Kullanım: <code>/rss_ekle [kategori] [kaynak_adı] [rss_url]</code>\n\nÖrnek: <code>/rss_ekle teknoloji ShiftDelete https://shiftdelete.net/feed</code>")
                    else:
                        category = parts[1].lower().strip()
                        name = parts[2].strip()
                        rss_url = parts[3].strip()
                        
                        cats = get_categories()
                        if category not in cats:
                            cats_str = ", ".join(f"<code>{c}</code>" for c in cats)
                            send_message(f"⚠️ Geçersiz kategori! Kullanabileceğiniz aktif kategoriler: {cats_str}")
                        else:
                            send_message(f"🔄 <code>{rss_url}</code> adresi test ediliyor...")
                            try:
                                response = requests.get(rss_url, timeout=10)
                                feed = feedparser.parse(response.text)
                            except Exception as e:
                                send_message(f"❌ RSS test isteği zaman aşımına uğradı veya başarısız oldu: {e}")
                                self.wfile.write(json.dumps({"status": "feed parse failed"}).encode())
                                return
                                
                            if not feed.entries:
                                send_message("❌ Geçersiz RSS adresi! Girilen bağlantıda geçerli haber beslemesi bulunamadı.")
                            else:
                                add_rss_source(name, rss_url, category)
                                send_success(
                                    "RSS Kaynağı Eklendi!",
                                    f"<b>İsim:</b> {html.escape(name)}\n<b>Kategori:</b> {category.upper()}\n<b>URL:</b> <code>{html.escape(rss_url)}</code>\n\n<i>Artık bu kaynaktan da otonom haber çekilecektir.</i>"
                                )
                except Exception as e:
                    send_message(f"⚠️ Kaynak eklenirken hata oluştu: {e}")
                    
            elif text.startswith("/rss_sil"):
                try:
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message("⚠️ Eksik parametre! Kullanım: <code>/rss_sil [kaynak_adı]</code>\n\nÖrnek: <code>/rss_sil Webtekno</code>")
                    else:
                        name_to_delete = parts[1].strip()
                        success = delete_rss_source(name_to_delete)
                        
                        if success:
                            send_success(
                                "RSS Kaynağı Silindi!",
                                f"<b>{name_to_delete}</b> isimli kaynak buluttan başarıyla temizlendi."
                            )
                        else:
                            send_message(f"⚠️ Firestore üzerinde <b>{name_to_delete}</b> isminde bir kaynak bulunamadı. Lütfen tam adı yazdığınızdan emin olun.")
                except Exception as e:
                    send_message(f"⚠️ Kaynak silinirken hata oluştu: {e}")
            else:
                # Custom topic news request
                try:
                    add_custom_request(text)
                    send_message(
                        f"🔍 <b>'{text}'</b> konusu otonom haber kuyruğuna başarıyla eklendi!\n\n"
                        f"⚡ <b>Bulut Yazarı (Cloud Builder)</b> konuyu araştırıp, yazacak ve birkaç dakika içinde yayına alacaktır.\n"
                        f"👉 Yayına girdiğinde tıklanabilir linkiyle birlikte onay mesajı buraya iletilecektir."
                    )
                except Exception as e:
                    send_error("Haber Talebi Kuyruğa Eklenemedi", f"İşlem sırasında hata oluştu: {e}")
                    
        except Exception as route_err:
            send_error("İşlem Hatası", f"İşlem sırasında hata oluştu: {route_err}")
            
        self.wfile.write(json.dumps({"status": "processed"}).encode())
