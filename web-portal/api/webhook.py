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
from dotenv import load_dotenv

# Environment configuration
load_dotenv(override=True)
if os.path.exists("backend-scripts/.env"):
    load_dotenv("backend-scripts/.env", override=True)
elif os.path.exists("../../backend-scripts/.env"):
    load_dotenv("../../backend-scripts/.env", override=True)


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

def get_gemini_api_keys():
    """Fetches Gemini API keys from environment variables or falls back to Firestore."""
    # 1. Environment variables check
    keys_str = os.getenv("GEMINI_API_KEYS")
    if keys_str:
        return [k.strip() for k in keys_str.split(",") if k.strip()]
        
    fallback_key = os.getenv("GEMINI_API_KEY")
    if fallback_key:
        return [fallback_key.strip()]
        
    # 2. Firestore fallback
    try:
        db = init_firebase()
        doc = db.collection("system_config").document("api_keys").get()
        if doc.exists:
            data = doc.to_dict()
            keys_val = data.get("gemini_api_keys")
            if keys_val:
                return [k.strip() for k in keys_val.split(",") if k.strip()]
    except Exception as e:
        print(f"Error fetching API keys from Firestore: {e}")
        
    return []

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

def get_research_config():
    """Fetches autonomous research config from Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("autonomous_research")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        is_active = data.get("is_active", True)
        interval_hours = data.get("interval_hours", 24)
        last_run_time = data.get("last_run_time", 0.0)
        is_running = data.get("is_running", False)
        inspiration_hours = data.get("inspiration_hours", 24)
        max_topics = data.get("max_topics", 2)
        return {
            "is_active": bool(is_active),
            "interval_hours": int(interval_hours),
            "last_run_time": float(last_run_time),
            "is_running": bool(is_running),
            "inspiration_hours": int(inspiration_hours),
            "max_topics": int(max_topics)
        }
    else:
        default_config = {
            "is_active": True,
            "interval_hours": 24,
            "last_run_time": 0.0,
            "is_running": False,
            "inspiration_hours": 24,
            "max_topics": 2
        }
        doc_ref.set(default_config)
        return default_config

def update_research_config(interval_hours=None, last_run_time=None, is_running=None, is_active=None, inspiration_hours=None, max_topics=None):
    """Updates autonomous research config on Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("autonomous_research")
    
    update_data = {}
    if interval_hours is not None:
        update_data["interval_hours"] = int(interval_hours)
    if last_run_time is not None:
        update_data["last_run_time"] = float(last_run_time)
    if is_running is not None:
        update_data["is_running"] = bool(is_running)
    if is_active is not None:
        update_data["is_active"] = bool(is_active)
    if inspiration_hours is not None:
        update_data["inspiration_hours"] = int(inspiration_hours)
    if max_topics is not None:
        update_data["max_topics"] = int(max_topics)
        
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
        return doc.to_dict().get("list", ["plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka", "akilli-ev"])
    else:
        default_cats = ["plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka", "akilli-ev"]
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
    category = "donanim-pratik"
    
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
                elif context == "benzer":
                    if metadata is not None:
                        # Update metadata and reset selected_ids for new analysis
                        data["metadata"] = metadata
                        data["selected_ids"] = []
                        doc_ref.set(data)
                        return []
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
    api_keys = get_gemini_api_keys()
    if not api_keys:
        print("HATA: Benzer haber kontrolü için GEMINI_API_KEYS veya GEMINI_API_KEY bulunamadı!")
        return "❌ <b>API Anahtarları Bulunamadı.</b>", []
            
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
        db = init_firebase()
        analysis_result = None
        duplicate_posts = []
        
        if is_toggle:
            # Try to read cached similarity analysis from bot_state document
            state_doc = db.collection("system_config").document("bot_state").get()
            if state_doc.exists:
                state_data = state_doc.to_dict()
                if state_data.get("state") == "multi_delete" and state_data.get("context") == "benzer":
                    metadata = state_data.get("metadata", {})
                    analysis_result = metadata.get("analysis_result")
                    raw_duplicates = metadata.get("duplicate_posts", [])
                    duplicate_posts = []
                    for item in raw_duplicates:
                        if isinstance(item, list) and len(item) == 2:
                            duplicate_posts.append((item[0], item[1]))
                        elif isinstance(item, tuple) and len(item) == 2:
                            duplicate_posts.append(item)
            
            # Fallback if cache is empty or incomplete
            if not analysis_result:
                analysis_result, duplicate_posts = check_similar_news_locally()
                selected_ids = get_or_init_multi_delete_state(chat_id, "benzer", metadata={
                    "analysis_result": analysis_result,
                    "duplicate_posts": duplicate_posts
                })
            else:
                selected_ids = get_or_init_multi_delete_state(chat_id, "benzer")
        else:
            # Fresh scan
            analysis_result, duplicate_posts = check_similar_news_locally()
            # Initialize state and cache the analysis
            selected_ids = get_or_init_multi_delete_state(chat_id, "benzer", metadata={
                "analysis_result": analysis_result,
                "duplicate_posts": duplicate_posts
            })
            
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
            {"text": "📝 Onay Bekleyen Haberler", "callback_data": "menu:bekleyenler"}
        ],
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
            {"text": "🧠 Otonom Araştırma", "callback_data": "menu:otoarastirma"}
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

def handle_pending_posts_list(callback_query, chat_id=None):
    """Fetches all pending approval posts and edits the callback message to show the list."""
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    if not chat_id:
        chat_id = callback_query["message"]["chat"]["id"]
        
    try:
        db = init_firebase()
        pending_docs = db.collection("pending_posts").where("status", "==", "pending_approval").get()
        
        docs_sorted = []
        for doc in pending_docs:
            data = doc.to_dict()
            docs_sorted.append((doc.id, data))
        docs_sorted.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
        
        if not docs_sorted:
            text = (
                "🟢 <b>Yayın Onayı Bekleyen Haber Yok!</b>\n\n"
                "Sistemde onayınızı bekleyen herhangi bir taslak bulunmuyor. Her şey güncel."
            )
            keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
        else:
            text = f"📝 <b>Yayın Onayı Bekleyen Haberler ({len(docs_sorted)} adet):</b>\n\nLütfen incelemek ve görüş yazmak istediğiniz haberi seçin:"
            keyboard = []
            for doc_id, data in docs_sorted[:15]:
                title = data.get("title", "Başlıksız")
                category = data.get("category", "genel").upper()
                if len(title) > 35:
                    title = title[:32] + "..."
                keyboard.append([{"text": f"📂 [{category}] {title}", "callback_data": f"review_pending:{doc_id}"}])
            
            if len(docs_sorted) > 15:
                text += f"\n\n💡 <i>Not: Toplam {len(docs_sorted)} bekleyen haber var. En yeni 15 tanesi listelenmektedir.</i>"
                
            keyboard.append([{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}])
            
        edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard}, chat_id=chat_id)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Taslak Listeleme Hatası", f"Hata: {e}")

def handle_review_pending_post(callback_query, doc_id):
    """Fetches details of a pending post and renders action buttons."""
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    try:
        db = init_firebase()
        doc = db.collection("pending_posts").document(doc_id).get()
        if not doc.exists:
            answer_callback_query(callback_id, "Taslak bulunamadı veya silinmiş.", show_alert=True)
            handle_pending_posts_list(callback_query, chat_id)
            return
            
        data = doc.to_dict()
        title = data.get("title", "Başlıksız")
        category = data.get("category", "genel").upper()
        summary = data.get("description", "Açıklama yok.")
        
        text = (
            f"📝 <b>Taslak Haber Detayı</b>\n"
            f"──────────────────────────────\n"
            f"📂 <b>Kategori:</b> {category}\n"
            f"📰 <b>Başlık:</b> {title}\n\n"
            f"🔍 <b>Özet:</b> {summary}\n"
            f"──────────────────────────────\n\n"
            f"✍️ Bu habere kendi görüşünüzü ekleyip yayınlamak için <b>✍️ Görüş Yaz</b> butonuna basarak açılan profesyonel kutucuğu kullanabilirsiniz."
        )
        
        keyboard = [
            [
                {"text": "📖 Haberi Oku", "url": f"https://ai-haber-portali.vercel.app/api/webhook?draft_id={doc_id}"},
                {"text": "✍️ Görüş Yaz", "web_app": {"url": f"https://ai-haber-portali.vercel.app/api/webhook?action=comment&draft_id={doc_id}&message_id={message_id}"}}
            ],
            [
                {"text": "🗑️ İptal Et / Sil", "callback_data": f"approve_delete:{doc_id}"},
                {"text": "🔙 Listeye Dön", "callback_data": "menu:bekleyenler"}
            ]
        ]
        
        edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard}, chat_id=chat_id)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Taslak Önizleme Hatası", f"Hata: {e}")

def send_pending_posts_list_message(chat_id):
    """Sends a new message with the pending approval posts list."""
    try:
        db = init_firebase()
        pending_docs = db.collection("pending_posts").where("status", "==", "pending_approval").get()
        
        docs_sorted = []
        for doc in pending_docs:
            data = doc.to_dict()
            docs_sorted.append((doc.id, data))
        docs_sorted.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
        
        if not docs_sorted:
            text = (
                "🟢 <b>Yayın Onayı Bekleyen Haber Yok!</b>\n\n"
                "Sistemde onayınızı bekleyen herhangi bir taslak bulunmuyor. Her şey güncel."
            )
            keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
        else:
            text = f"📝 <b>Yayın Onayı Bekleyen Haberler ({len(docs_sorted)} adet):</b>\n\nLütfen incelemek ve görüş yazmak istediğiniz haberi seçin:"
            keyboard = []
            for doc_id, data in docs_sorted[:15]:
                title = data.get("title", "Başlıksız")
                category = data.get("category", "genel").upper()
                if len(title) > 35:
                    title = title[:32] + "..."
                keyboard.append([{"text": f"📂 [{category}] {title}", "callback_data": f"review_pending:{doc_id}"}])
            
            if len(docs_sorted) > 15:
                text += f"\n\n💡 <i>Not: Toplam {len(docs_sorted)} bekleyen haber var. En yeni 15 tanesi listelenmektedir.</i>"
                
            keyboard.append([{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}])
            
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = {
            "chat_id": str(chat_id).strip(),
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": keyboard}
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        send_error("Taslak Mesajı Gönderme Hatası", f"Hata: {e}")


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
        
        elapsed_min = (time.time() - last_run_val) / 60.0
        next_run_min = max(0.0, interval_val - elapsed_min)
        
        from datetime import timezone
        tr_tz = timezone(timedelta(hours=3))
        last_run_str = datetime.fromtimestamp(last_run_val, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S")
        next_run_str = (datetime.now(tr_tz) + timedelta(minutes=next_run_min)).strftime("%d.%m.%Y %H:%M:%S")
        
        status_msg = (
            "📊 <b>Sistem Durum Raporu (Bulut Entegreli)</b>\n\n"
            "📡 <b>RSS TARAYICI VE YAZICI:</b>\n"
            f"• <b>Otonom Tarayıcı:</b> {'🟢 Aktif' if is_active_val else '🔴 Pasif'}\n"
            f"• <b>Çalışma Durumu:</b> {'⚡ Tarama Yapılıyor...' if is_running_val else '💤 Beklemede'}\n"
            f"• <b>Tarama Sıklığı:</b> {interval_val} dakikada bir\n"
            f"• <b>Son Tarama Zamanı:</b> {last_run_str}\n"
            f"• <b>Sonraki Tarama:</b> {next_run_str} (~{int(next_run_min)} dakika sonra)\n\n"
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
        
    # Standard protection: do not let them delete core categories
    if cat_slug in ["plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka", "akilli-ev"]:
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
            cat = p.get("category", "donanim-pratik").lower()
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
        
        cat_posts = [(p_id, p) for p_id, p in posts.items() if p["date"] == date_val and p.get("category", "donanim-pratik").lower() == category_val.lower()]
        
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
            f"<b>Kategori:</b> {p.get('category', 'donanim-pratik').upper()}\n"
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
    
    edit_message_text("⏳ <b>Haber silme kuyruğuna alınıyor, lütfen bekleyin...</b>", message_id)
    answer_callback_query(callback_id, "Silme işlemi başlatıldı.")
    
    try:
        index_data = get_posts_index()
        posts = index_data.get("posts", {})
        
        p = posts.get(p_id)
        if not p:
            edit_message_text("❌ Hata: Haber bilgisi güncel indeks içinde bulunamadı.", message_id)
            return
            
        slug = p["slug"]
        image_url = p.get("image", "")
        img_name = os.path.basename(image_url) if image_url else ""
        
        db = init_firebase()
        
        # 1. Add to deletion queue in Firestore
        db.collection("deletion_queue").add({
            "slug": slug,
            "image_name": img_name,
            "type": "published",
            "status": "pending",
            "queued_at": time.time()
        })
        
        # 2. Fetch markdown from GitHub (read-only) to extract sourceUrl for blacklist
        blacklist_status = "Bulunamadı"
        try:
            owner = "kemaleris8391-dev"
            repo = "ai-haber-portali"
            md_path = f"web-portal/src/content/blog/{slug}"
            md_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{md_path}"
            headers = get_github_headers()
            r_get = requests.get(md_url, headers=headers, timeout=10)
            if r_get.status_code == 200:
                content_b64 = r_get.json().get("content", "")
                if content_b64:
                    import base64
                    md_text = base64.b64decode(content_b64).decode("utf-8")
                    import re
                    src_match = re.search(r'^sourceUrl:\s*["\']?(.*?)["\']?\s*$', md_text, re.MULTILINE)
                    if src_match:
                        source_url = src_match.group(1).strip()
                        if source_url:
                            if add_to_blacklist_in_webhook(source_url):
                                blacklist_status = "Aktif (URL Engellendi)"
        except Exception as e:
            print(f"Error blacklisting single published post {slug}: {e}")
            
        # 3. Remove from index locally in Firestore
        remove_posts_from_index_locally([p_id])
        
        escaped_title = html.escape(p['title'])
        success_msg = (
            "🗑️ <b>Haber Silme Kuyruğuna Alındı!</b>\n\n"
            f"<b>Silinen Haber:</b> {escaped_title}\n"
            f"<b>Kara Liste:</b> <code>{blacklist_status}</code>\n\n"
            "Haber listeden kaldırıldı ve gece yarısından sonra otomatik olarak temizlenecektir."
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
    
    edit_message_text("⏳ <b>Haberler silme kuyruğuna alınıyor, lütfen bekleyin...</b>", message_id)
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
        
        success_queued = []
        
        owner = "kemaleris8391-dev"
        repo = "ai-haber-portali"
        headers = get_github_headers()
        
        for p_id in selected_ids:
            p = posts.get(p_id)
            if not p:
                continue
                
            slug = p["slug"]
            image_url = p.get("image", "")
            img_name = os.path.basename(image_url) if image_url else ""
            
            # 1. Add to deletion queue in Firestore
            db.collection("deletion_queue").add({
                "slug": slug,
                "image_name": img_name,
                "type": "published",
                "status": "pending",
                "queued_at": time.time()
            })
            
            # 2. Fetch markdown from GitHub (read-only) to extract sourceUrl for blacklist
            try:
                md_path = f"web-portal/src/content/blog/{slug}"
                md_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{md_path}"
                r_get = requests.get(md_url, headers=headers, timeout=10)
                if r_get.status_code == 200:
                    content_b64 = r_get.json().get("content", "")
                    if content_b64:
                        import base64
                        md_text = base64.b64decode(content_b64).decode("utf-8")
                        import re
                        src_match = re.search(r'^sourceUrl:\s*["\']?(.*?)["\']?\s*$', md_text, re.MULTILINE)
                        if src_match:
                            source_url = src_match.group(1).strip()
                            if source_url:
                                add_to_blacklist_in_webhook(source_url)
            except Exception as e:
                print(f"Error blacklisting published post {slug}: {e}")
                
            success_queued.append(p)
            
        # Remove from index immediately so they disappear from frontend listings
        if success_queued:
            success_ids = [p_id for p_id in selected_ids if posts.get(p_id)]
            remove_posts_from_index_locally(success_ids)
            
        # Clear bot state
        db.collection("system_config").document("bot_state").delete()
        
        report_msg = ""
        if success_queued:
            success_details = "\n".join([f"• {html.escape(p['title'])}" for p in success_queued])
            report_msg += f"✅ <b>Silme Kuyruğuna Alınan Haberler ({len(success_queued)} adet):</b>\n{success_details}\n\n"
            report_msg += (
                "Haberler listeden kaldırıldı ve gece yarısından sonra otomatik olarak temizlenecektir.\n"
                "Ayrıca tekrar taranmamaları için kaynak URL'leri kara listeye eklenmiştir."
            )
        else:
            report_msg = "❌ Hiçbir haber silinemedi veya seçilen haberler bulunamadı."
            
        keyboard = [[{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]]
        edit_message_text(report_msg, message_id, reply_markup={"inline_keyboard": keyboard})
        
    except Exception as e:
        send_error("Çoklu Haber Silme Başarısız", f"Silme işlemi sırasında kritik hata: {e}")
        edit_message_text(f"❌ Haberler silinirken hata oluştu: <code>{e}</code>", message_id)

import base64

def get_github_headers():
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_PAT veya GITHUB_TOKEN tanımlı değil!")
    return {
        "Authorization": f"Bearer {github_token.strip()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AIHABERLER-Bot"
    }

def publish_markdown_to_github(slug, markdown_content):
    import base64
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    path = f"web-portal/src/content/blog/{slug}.md"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    headers = get_github_headers()
    
    sha = None
    r_get = requests.get(url, headers=headers, timeout=10)
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")
        
    content_b64 = base64.b64encode(markdown_content.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": f"feat: publish news '{slug}' via Telegram Bot approval",
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha
        
    r_put = requests.put(url, json=payload, headers=headers, timeout=15)
    return r_put.status_code in [200, 201]

def delete_file_from_github(path, commit_message):
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    headers = get_github_headers()
    
    r_get = requests.get(url, headers=headers, timeout=10)
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")
        if sha:
            payload = {
                "message": commit_message,
                "sha": sha
            }
            r_del = requests.delete(url, json=payload, headers=headers, timeout=15)
            return r_del.status_code == 200
    return False

def handle_approve_direct(callback_query, doc_id):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    warning_text = (
        "⚠️ <b>Yorumsuz doğrudan yayınlama özelliği devre dışı bırakılmıştır.</b>\n\n"
        "Lütfen bu habere kendi görüşünüzü ekleyip yayınlamak için mesaja <b>YANIT (Reply) yazıp gönderin</b>."
    )
    edit_message_text(warning_text, message_id)
    answer_callback_query(callback_id, "Bu özellik devre dışıdır.", show_alert=True)

def add_to_blacklist_in_webhook(source_url):
    try:
        db = init_firebase()
        doc_ref = db.collection("system_config").document("blacklisted_links")
        doc = doc_ref.get()
        now = time.time()
        
        current_links = {}
        if doc.exists:
            data = doc.to_dict()
            links_data = data.get("links", {})
            if isinstance(links_data, dict):
                current_links = links_data
            elif isinstance(links_data, list):
                current_links = {link: now for link in links_data}
                
        if source_url not in current_links:
            current_links[source_url] = now
            doc_ref.set({
                "links": current_links,
                "last_updated": now
            })
            print(f"URL blacklisted successfully in webhook: {source_url}")
            return True
    except Exception as e:
        print(f"Error adding to blacklist in webhook: {e}")
    return False

def handle_approve_delete(callback_query, doc_id):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    
    edit_message_text("⏳ <b>Taslak silme kuyruğuna alınıyor, lütfen bekleyin...</b>", message_id)
    answer_callback_query(callback_id, "Silme işlemi başlatıldı.")
    
    try:
        db = init_firebase()
        doc_ref = db.collection("pending_posts").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            edit_message_text("❌ Hata: Taslak haber bulunamadı veya zaten silinmiş.", message_id)
            return
            
        post_data = doc.to_dict()
        slug = post_data["slug"]
        image_url = post_data.get("heroImage", "")
        source_url = post_data.get("sourceUrl", "")
        
        # 1. Update draft status in pending_posts to queued_for_deletion
        doc_ref.update({
            "status": "queued_for_deletion",
            "queued_for_deletion_at": time.time()
        })
        
        # 2. Add to deletion queue
        img_name = os.path.basename(image_url) if image_url else ""
        db.collection("deletion_queue").add({
            "slug": slug,
            "image_name": img_name,
            "type": "draft",
            "status": "pending",
            "queued_at": time.time()
        })
        
        # 3. Add to blacklist immediately so crawler skips it
        blacklist_status = "Başarısız"
        if source_url:
            if add_to_blacklist_in_webhook(source_url):
                blacklist_status = "Aktif (URL Engellendi)"
                
        success_text = (
            "🗑️ <b>Taslak Haber Silme Kuyruğuna Alındı!</b>\n\n"
            f"<b>Başlık:</b> {html.escape(post_data['title'])}\n"
            f"<b>Kategori:</b> {post_data['category'].upper()}\n"
            f"<b>Kara Liste:</b> <code>{blacklist_status}</code>\n\n"
            "Taslak haber silinmek üzere kuyruğa alındı ve gece yarısından sonra otomatik olarak temizlenecektir."
        )
        keyboard = [
            [{"text": "🔙 Bekleyenler Listesine Dön", "callback_data": "menu:bekleyenler"}],
            [{"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}]
        ]
        edit_message_text(success_text, message_id, reply_markup={"inline_keyboard": keyboard})
        
    except Exception as e:
        edit_message_text(f"❌ Taslak silinirken hata oluştu: <code>{e}</code>", message_id)

def enrich_news_with_comment(draft_data, user_comment):
    api_keys = get_gemini_api_keys()
    if not api_keys:
        raise ValueError("API anahtarları bulunamadı!")
        
    prompt = f"""
Aşağıda yapay zeka tarafından yazılmış bir haber makalesi ve bu makalenin en tepesine eklenecek olan editörün kişisel tecrübesi/görüşü yer almaktadır.

GÖREVİN:
1. Editörün kişisel tecrübesini/görüşünü incele. Harf hataları veya basit yazım hataları varsa düzelt ancak konuşma tonunu, teknik üslubunu, samimiyetini, argolarını, teknik terimlerini ve düşüncelerini KESİNLİKLE değiştirme, yumuşatma veya resmileştirme. Onun usta ve tecrübeli editör kimliğini, samimi sesini aynen koru.
2. Bu yorumu makale metninin EN TEPESİNE (ilk paragrafa), yapay zeka tarafından yazılmadığı, bizzat bir insan görüşü olduğu açıkça anlaşılan özel bir stil halinde ekle:
   > 💬 **Editörün Kaleminden:** [Editörün yorumunu/görüşünü kelimesi kelimesine, tonunu bozmadan buraya yerleştir]
   
   Ardından bir boşluk bırakıp makalenin orijinal içeriğini devam ettir.
3. Haberin başlığını, editörün kişisel tecrübesinin/görüşünün ana fikrini içerecek veya onun görüşünü yansıtacak şekilde güncelle. Başlığın en başında veya içinde editörün görüşü ana fikir olmalıdır.
4. Çıktıyı kesinlikle aşağıdaki JSON formatında ver (başka açıklama ekleme, markdown kod bloğu içinde olmalıdır):
```json
{{
  "title": "[Yeni Başlık]",
  "content": "[Yeni İçerik]"
}}
```

Makale Başlığı: {draft_data['title']}
Makale İçeriği:
{draft_data['content']}

Editörün Kişisel Görüşü:
{user_comment}
"""

    models_to_try = ["gemma-4-31b-it", "gemma-4-26b-a4b-it", "gemma-4-26b-it", "gemini-2.5-flash"]
    last_err = "Bilinmeyen API Hatası"
    
    for key in api_keys:
        try:
            client = genai.Client(api_key=key)
            for model_name in models_to_try:
                try:
                    print(f"Gemma ile yorum entegrasyonu deneniyor: Model={model_name} (Key: {key[-6:]})...")
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                thinking_config=types.ThinkingConfig(
                                    thinking_level="HIGH"
                                )
                            )
                        )
                    except Exception as thinking_err:
                        print(f"Model {model_name} thinking_config hatası. Normal modda deneniyor...")
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                            )
                        )
                    
                    text = response.text
                    if not text:
                        continue
                        
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                        
                    data = json.loads(text.strip())
                    if data.get("title") and data.get("content"):
                        return data
                except Exception as model_err:
                    last_err = str(model_err)
                    print(f"Model {model_name} zenginleştirme hatası: {last_err}")
                    continue
        except Exception as e:
            last_err = str(e)
            print(f"API key hatası (Key: {key[-6:]}): {last_err}")
            continue
            
    raise Exception(f"Gemma 31B Zenginleştirme Hatası: {last_err}")

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
        answer_callback_query(callback_query["id"], "🧹 Otonom Temizlik Sistemi Kaldırılmıştır.", show_alert=True)
    elif data.startswith("ototemizlik_toggle:"):
        answer_callback_query(callback_query["id"], "🧹 Bu özellik devre dışı bırakılmıştır.", show_alert=True)
    elif data.startswith("set_temizlik_sure:"):
        answer_callback_query(callback_query["id"], "🧹 Bu özellik devre dışı bırakılmıştır.", show_alert=True)
    elif data == "ototemizlik_manuel":
        answer_callback_query(callback_query["id"], "🧹 Bu özellik devre dışı bırakılmıştır.", show_alert=True)
    elif data == "menu:otoarastirma":
        handle_otoarastirma_menu(callback_query)
    elif data.startswith("research_toggle:"):
        set_to = data.split(":", 1)[1]
        is_active = (set_to == "on")
        update_research_config(is_active=is_active)
        answer_callback_query(callback_query["id"], f"🧠 Otonom Araştırma {'aktif' if is_active else 'pasif'} yapıldı!", show_alert=True)
        handle_otoarastirma_menu(callback_query)
    elif data.startswith("research_freq_set:"):
        hours = int(data.split(":", 1)[1])
        update_research_config(interval_hours=hours)
        answer_callback_query(callback_query["id"], f"⏱️ Tarama tetikleme zamanı {hours} saat yapıldı!", show_alert=True)
        handle_otoarastirma_menu(callback_query)
    elif data.startswith("research_insp_set:"):
        hours = int(data.split(":", 1)[1])
        update_research_config(inspiration_hours=hours)
        answer_callback_query(callback_query["id"], f"🔍 Geriye dönük tarama zamanı {hours} saat yapıldı!", show_alert=True)
        handle_otoarastirma_menu(callback_query)
    elif data.startswith("research_limit_set:"):
        limit = int(data.split(":", 1)[1])
        update_research_config(max_topics=limit)
        answer_callback_query(callback_query["id"], f"✍️ Yazım adedi {limit} haber yapıldı!", show_alert=True)
        handle_otoarastirma_menu(callback_query)
    elif data == "research_trigger_now":
        success = trigger_github_workflow(research=True)
        if success:
            answer_callback_query(callback_query["id"], "Otonom araştırma tetiklendi!")
            edit_message_text(
                "⚡ <b>Manuel Otonom Araştırma Tetiklendi!</b>\n\n"
                "GitHub Actions bulut sunucusu üzerinde otonom haber araştırma işlemi başarıyla başlatıldı.\n"
                "🔍 Son eklenen haberlerden ilham alınarak Google Arama Grounding ile tamamen yeni, özgün ve telif hakkı kurallarına uygun araştırma makaleleri yazılacaktır.\n\n"
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
    elif data.startswith("approve_direct:"):
        doc_id = data.split(":", 1)[1]
        handle_approve_direct(callback_query, doc_id)
    elif data.startswith("approve_delete:"):
        doc_id = data.split(":", 1)[1]
        handle_approve_delete(callback_query, doc_id)
    elif data == "menu:bekleyenler":
        handle_pending_posts_list(callback_query)
    elif data.startswith("review_pending:"):
        doc_id = data.split(":", 1)[1]
        handle_review_pending_post(callback_query, doc_id)

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
def trigger_github_workflow(research=False):
    """Triggers GitHub Actions workflow via dispatch API or falls back to Firestore trigger."""
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    workflow_id = "autonomous_rss.yml"
    
    # 1. Firestore Meşguliyet Kontrolü (Otonom / Manuel Çakışma Önleme)
    try:
        sched_conf = get_scheduler_config()
        if sched_conf.get("is_running", False):
            last_run = sched_conf.get("last_run_time", 0.0)
            elapsed_minutes = (time.time() - last_run) / 60.0
            if elapsed_minutes < 15.0:
                send_message(
                    "⚠️ <b>Aktif Tarama Zaten Devam Ediyor!</b>\n\n"
                    "Sistem şu anda otonom veya manuel olarak tetiklenmiş bir tarama işlemi yürütmektedir.\n\n"
                    "🚫 <b>Çakışma Koruması:</b> Aynı anda birden fazla tarama yapılması, haberlerin mükerrer yazılmasına veya sunucu hatalarına yol açabileceği için şu an tetikleme yapılamaz.\n\n"
                    "⏳ <i>Lütfen mevcut işlemin bitmesini (yaklaşık 1-2 dakika) bekleyin.</i>"
                )
                return False
            else:
                print(f"BİLGİ: Kilit takılı kalmış ({elapsed_minutes:.1f} dakika önce). Sıfırlanıyor...")
                update_scheduler_config(is_running=False)
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
            now_utc = datetime.utcnow()
            
            if r_prog.status_code == 200:
                for run in r_prog.json().get("workflow_runs", []):
                    created_at_str = run.get("created_at")
                    if created_at_str:
                        try:
                            dt = datetime.strptime(created_at_str[:19], "%Y-%m-%dT%H:%M:%S")
                            elapsed_run_minutes = (now_utc - dt).total_seconds() / 60.0
                            if elapsed_run_minutes < 20.0:
                                active_runs += 1
                        except Exception as parse_err:
                            print(f"Error parsing created_at: {parse_err}")
                            active_runs += 1
                    else:
                        active_runs += 1
                        
            if r_queue.status_code == 200:
                for run in r_queue.json().get("workflow_runs", []):
                    created_at_str = run.get("created_at")
                    if created_at_str:
                        try:
                            dt = datetime.strptime(created_at_str[:19], "%Y-%m-%dT%H:%M:%S")
                            elapsed_run_minutes = (now_utc - dt).total_seconds() / 60.0
                            if elapsed_run_minutes < 20.0:
                                active_runs += 1
                        except Exception as parse_err:
                            print(f"Error parsing created_at: {parse_err}")
                            active_runs += 1
                    else:
                        active_runs += 1
                        
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
            
    req_type = "otonom araştırma" if research else "tarama"
    send_message(f"🔄 <b>Manuel {req_type} isteği alındı.</b> Bulut sunucusu (GitHub Actions) ile bağlantı kuruluyor...")
    
    if not github_token:
        # Fallback to scheduling
        try:
            update_scheduler_config(last_run_time=0, is_running=False)
            send_success(
                f"İşlem Sıraya Eklendi (Bulut Zamanlayıcı)",
                f"GitHub erişim anahtarı (<code>GITHUB_PAT</code>) yapılandırılmadığı için işlem bulut zamanlayıcısına (Cron) havale edildi.\n\n"
                f"⚡ <b>Bulut Yazarı</b> en geç <b>10 dakika içinde</b> otomatik olarak uyanacak, işlemi yapacak ve yeni haberleri yayınlayacaktır.\n\n"
                f"💡 <i>Öneri: Vercel panelinden <code>GITHUB_PAT</code> anahtarını tanımlayarak tetiklemelerin anında (1 saniyede) gerçekleşmesini sağlayabilirsiniz!</i>"
            )
        except Exception as e:
            send_error("Manuel Tetikleme Hatası", f"Firestore zamanlayıcı tetiklenirken hata oluştu: {e}")
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
            "force": "true",
            "research": "true" if research else "false"
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 204:
            title_text = "Otonom Araştırma Tetiklendi!" if research else "Bulut Taraması Tetiklendi!"
            desc_text = (
                "🚀 <b>GitHub Actions Bulut Sunucusu ANINDA tetiklendi!</b>\n\n"
                "Yapay zeka yazarımız son haberlerden esinlenen otonom araştırma konularını yazmaya başladı.\n"
                "👉 İşlem tamamlandığında (yaklaşık 2-3 dakika) yeni makalelerin linklerini içeren başarı raporu doğrudan buraya iletilecektir."
            ) if research else (
                "🚀 <b>GitHub Actions Bulut Sunucusu ANINDA tetiklendi!</b>\n\n"
                "Yapay zeka yazarımız bulutta RSS kaynaklarını taramaya ve makaleleri yazmaya başladı.\n"
                "👉 İşlem tamamlandığında (yaklaşık 2-3 dakika) yeni haberlerin tıklanabilir linklerini içeren başarı raporu doğrudan buraya iletilecektir."
            )
            send_success(title_text, desc_text)
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
            last_run = sched_conf.get("last_run_time", 0.0)
            elapsed_minutes = (time.time() - last_run) / 60.0
            if elapsed_minutes < 15.0:
                send_message(
                    "⚠️ <b>Aktif İşlem Zaten Devam Ediyor!</b>\n\n"
                    "Sistem şu anda otonom veya manuel olarak tetiklenmiş bir tarama/temizlik işlemi yürütmektedir.\n\n"
                    "⏳ <i>Lütfen mevcut işlemin bitmesini bekleyin.</i>"
                )
                return False
            else:
                print(f"BİLGİ: Temizlik öncesi kilit takılı kalmış ({elapsed_minutes:.1f} dakika önce). Sıfırlanıyor...")
                update_scheduler_config(is_running=False)
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
            now_utc = datetime.utcnow()
            
            if r_prog.status_code == 200:
                for run in r_prog.json().get("workflow_runs", []):
                    created_at_str = run.get("created_at")
                    if created_at_str:
                        try:
                            dt = datetime.strptime(created_at_str[:19], "%Y-%m-%dT%H:%M:%S")
                            elapsed_run_minutes = (now_utc - dt).total_seconds() / 60.0
                            if elapsed_run_minutes < 20.0:
                                active_runs += 1
                        except Exception as parse_err:
                            print(f"Error parsing created_at: {parse_err}")
                            active_runs += 1
                    else:
                        active_runs += 1
                        
            if r_queue.status_code == 200:
                for run in r_queue.json().get("workflow_runs", []):
                    created_at_str = run.get("created_at")
                    if created_at_str:
                        try:
                            dt = datetime.strptime(created_at_str[:19], "%Y-%m-%dT%H:%M:%S")
                            elapsed_run_minutes = (now_utc - dt).total_seconds() / 60.0
                            if elapsed_run_minutes < 20.0:
                                active_runs += 1
                        except Exception as parse_err:
                            print(f"Error parsing created_at: {parse_err}")
                            active_runs += 1
                    else:
                        active_runs += 1
                        
            if active_runs > 0:
                send_message(
                    "⚠️ <b>Bulul Sunucusu Şu Anda Meşgul!</b>\n\n"
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

def handle_otoarastirma_menu(callback_query):
    message_id = callback_query["message"]["message_id"]
    callback_id = callback_query["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    try:
        config = get_research_config()
        is_active = config.get("is_active", True)
        interval_hours = config.get("interval_hours", 24)
        last_run = config.get("last_run_time", 0.0)
        inspiration_hours = config.get("inspiration_hours", 24)
        max_topics = config.get("max_topics", 2)
        
        status_text = "🟢 AKTİF (OTOMATİK ÇALIŞIYOR)" if is_active else "🔴 PASİF (DURDURULDU)"
        
        from datetime import timezone
        tr_tz = timezone(timedelta(hours=3))
        if last_run > 0:
            last_run_str = datetime.fromtimestamp(last_run, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S")
        else:
            last_run_str = "Hiç çalıştırılmadı"
            
        text = (
            "🧠 <b>Otonom Haber Araştırma Paneli</b> 🧠\n"
            "──────────────────────────────\n"
            f"🎯 <b>Mevcut Durum:</b> {status_text}\n"
            f"⏱️ <b>Tarama Tetikleme Zamanı:</b> Her {interval_hours} saatte bir\n"
            f"🔍 <b>Geriye Dönük Tarama Zamanı:</b> Son {inspiration_hours} saatlik haberlerden esinlenilir\n"
            f"✍️ <b>Yazım Adedi:</b> Çalışma başına maks {max_topics} haber üretilir\n"
            f"📅 <b>Son Araştırma Zamanı:</b> {last_run_str}\n\n"
            "──────────────────────────────\n"
            "📖 <b>Açıklayıcı Bilgi:</b>\n"
            "• Sistem, belirlediğiniz tetikleme saati dolduğunda (örn: 1 veya 2 saatte bir) otonom çalışır.\n"
            "• Belirlenen geriye dönük saat dilimindeki (örn: son 12 veya 24 saatlik) eklenmiş haberleri inceleyerek yepyeni **araştırma konuları** bulur.\n"
            "• Bu konuları <b>Google Arama</b> ile araştırıp tamamen özgün makaleler yazar ve yayınlar.\n"
            "──────────────────────────────\n\n"
            "Aşağıdaki butonları kullanarak otonom araştırma ayarlarını yönetebilirsiniz:\n"
            "⏱️: Tarama Tetikleme Zamanı | 🔍: Geriye Dönük Tarama Zamanı | ✍️: Yazım Adedi"
        )
        
        keyboard = [
            [
                {"text": f"{'🔴 Kapat (Devre Dışı Bırak)' if is_active else '🟢 Aktifleştir (Çalıştır)'}", "callback_data": f"research_toggle:{'off' if is_active else 'on'}"}
            ],
            [
                {"text": "⏱️ 1S" if interval_hours == 1 else "1S", "callback_data": "research_freq_set:1"},
                {"text": "⏱️ 2S" if interval_hours == 2 else "2S", "callback_data": "research_freq_set:2"},
                {"text": "⏱️ 3S" if interval_hours == 3 else "3S", "callback_data": "research_freq_set:3"},
                {"text": "⏱️ 4S" if interval_hours == 4 else "4S", "callback_data": "research_freq_set:4"}
            ],
            [
                {"text": "🔍 6S" if inspiration_hours == 6 else "6S", "callback_data": "research_insp_set:6"},
                {"text": "🔍 12S" if inspiration_hours == 12 else "12S", "callback_data": "research_insp_set:12"},
                {"text": "🔍 24S" if inspiration_hours == 24 else "24S", "callback_data": "research_insp_set:24"},
                {"text": "🔍 48S" if inspiration_hours == 48 else "48S", "callback_data": "research_insp_set:48"}
            ],
            [
                {"text": "✍️ 1" if max_topics == 1 else "1", "callback_data": "research_limit_set:1"},
                {"text": "✍️ 2" if max_topics == 2 else "2", "callback_data": "research_limit_set:2"},
                {"text": "✍️ 3" if max_topics == 3 else "3", "callback_data": "research_limit_set:3"},
                {"text": "✍️ 5" if max_topics == 5 else "5", "callback_data": "research_limit_set:5"}
            ],
            [
                {"text": "⚡ Şimdi Araştır (Manuel)", "callback_data": "research_trigger_now"},
                {"text": "🔙 Ana Menüye Dön", "callback_data": "menu:yardim"}
            ]
        ]
        
        edit_message_text(text, message_id, reply_markup={"inline_keyboard": keyboard}, chat_id=chat_id)
        answer_callback_query(callback_id)
    except Exception as e:
        send_error("Otonom Araştırma Panel Hatası", f"Hata: {e}")

def send_otoarastirma_menu_message():
    try:
        config = get_research_config()
        is_active = config.get("is_active", True)
        interval_hours = config.get("interval_hours", 24)
        last_run = config.get("last_run_time", 0.0)
        inspiration_hours = config.get("inspiration_hours", 24)
        max_topics = config.get("max_topics", 2)
        
        status_text = "🟢 AKTİF (OTOMATİK ÇALIŞIYOR)" if is_active else "🔴 PASİF (DURDURULDU)"
        
        from datetime import timezone
        tr_tz = timezone(timedelta(hours=3))
        if last_run > 0:
            last_run_str = datetime.fromtimestamp(last_run, tz=tr_tz).strftime("%d.%m.%Y %H:%M:%S")
        else:
            last_run_str = "Hiç çalıştırılmadı"
            
        text = (
            "🧠 <b>Otonom Haber Araştırma Paneli</b> 🧠\n"
            "──────────────────────────────\n"
            f"🎯 <b>Mevcut Durum:</b> {status_text}\n"
            f"⏱️ <b>Tarama Tetikleme Zamanı:</b> Her {interval_hours} saatte bir\n"
            f"🔍 <b>Geriye Dönük Tarama Zamanı:</b> Son {inspiration_hours} saatlik haberlerden esinlenilir\n"
            f"✍️ <b>Yazım Adedi:</b> Çalışma başına maks {max_topics} haber üretilir\n"
            f"📅 <b>Son Araştırma Zamanı:</b> {last_run_str}\n\n"
            "──────────────────────────────\n"
            "📖 <b>Açıklayıcı Bilgi:</b>\n"
            "• Sistem, belirlediğiniz tetikleme saati dolduğunda (örn: 1 veya 2 saatte bir) otonom çalışır.\n"
            "• Belirlenen geriye dönük saat dilimindeki (örn: son 12 veya 24 saatlik) eklenmiş haberleri inceleyerek yepyeni **araştırma konuları** bulur.\n"
            "• Bu konuları <b>Google Arama</b> ile araştırıp tamamen özgün makaleler yazar ve yayınlar.\n"
            "──────────────────────────────\n\n"
            "Aşağıdaki butonları kullanarak otonom araştırma ayarlarını yönetebilirsiniz:\n"
            "⏱️: Tarama Tetikleme Zamanı | 🔍: Geriye Dönük Tarama Zamanı | ✍️: Yazım Adedi"
        )
        
        keyboard = [
            [
                {"text": f"{'🔴 Kapat (Devre Dışı Bırak)' if is_active else '🟢 Aktifleştir (Çalıştır)'}", "callback_data": f"research_toggle:{'off' if is_active else 'on'}"}
            ],
            [
                {"text": "⏱️ 1S" if interval_hours == 1 else "1S", "callback_data": "research_freq_set:1"},
                {"text": "⏱️ 2S" if interval_hours == 2 else "2S", "callback_data": "research_freq_set:2"},
                {"text": "⏱️ 3S" if interval_hours == 3 else "3S", "callback_data": "research_freq_set:3"},
                {"text": "⏱️ 4S" if interval_hours == 4 else "4S", "callback_data": "research_freq_set:4"}
            ],
            [
                {"text": "🔍 6S" if inspiration_hours == 6 else "6S", "callback_data": "research_insp_set:6"},
                {"text": "🔍 12S" if inspiration_hours == 12 else "12S", "callback_data": "research_insp_set:12"},
                {"text": "🔍 24S" if inspiration_hours == 24 else "24S", "callback_data": "research_insp_set:24"},
                {"text": "🔍 48S" if inspiration_hours == 48 else "48S", "callback_data": "research_insp_set:48"}
            ],
            [
                {"text": "✍️ 1" if max_topics == 1 else "1", "callback_data": "research_limit_set:1"},
                {"text": "✍️ 2" if max_topics == 2 else "2", "callback_data": "research_limit_set:2"},
                {"text": "✍️ 3" if max_topics == 3 else "3", "callback_data": "research_limit_set:3"},
                {"text": "✍️ 5" if max_topics == 5 else "5", "callback_data": "research_limit_set:5"}
            ],
            [
                {"text": "⚡ Şimdi Araştır (Manuel)", "callback_data": "research_trigger_now"},
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
        print(f"Error sending otoarastirma menu: {e}")

# VERCEL SERVERLESS HANDLER
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serves draft preview page for review before publishing."""
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        draft_id_list = params.get("draft_id")
        
        if not draft_id_list:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("❌ <b>Hata:</b> Geçersiz istek. Lütfen geçerli bir draft_id belirtin.".encode('utf-8'))
            return
            
        draft_id = draft_id_list[0].strip()
        db = init_firebase()
        doc = db.collection("pending_posts").document(draft_id).get()
        
        if not doc.exists:
            self.send_response(404)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"❌ <b>Hata:</b> {draft_id} kimlikli taslak haber bulunamadı veya zaten yayınlandı/silindi.".encode('utf-8'))
            return
            
        action_list = params.get("action")
        action = action_list[0].strip() if action_list else ""
        
        post_data = doc.to_dict()
        title = post_data.get("title", "Taslak Haber")
        description = post_data.get("description", "")
        content = post_data.get("content", "")
        category = post_data.get("category", "genel").upper()
        source_name = post_data.get("sourceName", "Kaynak")
        source_url = post_data.get("sourceUrl", "#")
        
        # Category neon colors mapping
        cat_colors = {
            "PLC": "#00f0ff",
            "PC": "#39ff14",
            "ENDUSTRIYEL-MAKINALAR": "#ff007f",
            "OYUN": "#f857a6",
            "YAPAY-ZEKA": "#bd00ff",
            "AKILLI-EV": "#ffb703"
        }
        accent_color = cat_colors.get(category, "#e4e4e7")
        
        from datetime import timezone, timedelta
        tr_tz = timezone(timedelta(hours=3))
        
        if action == "comment":
            html_page = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Görüş Yaz ve Yayınla</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {{
            --bg-color: #03001e;
            --accent-color: {accent_color};
            --text-color: #f3f4f6;
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.08);
            --shadow-glow: 0 0 25px rgba(189, 0, 255, 0.15);
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background: #03001e;
            color: var(--text-color);
            font-family: 'Outfit', sans-serif;
            line-height: 1.6;
            padding: 1.5rem 1rem;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .container {{
            width: 100%;
            max-width: 500px;
        }}
        
        .glass-card {{
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), var(--shadow-glow);
        }}
        
        .badge {{
            display: inline-block;
            color: var(--accent-color);
            border: 1px solid var(--accent-color);
            background: rgba(255, 255, 255, 0.02);
            padding: 0.3rem 0.8rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            margin-bottom: 1rem;
            text-transform: uppercase;
        }}
        
        h2 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: #ffffff;
            line-height: 1.3;
        }}
        
        label {{
            display: block;
            font-size: 0.9rem;
            color: #9ca3af;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }}
        
        textarea {{
            width: 100%;
            height: 150px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            padding: 1rem;
            color: #ffffff;
            font-family: inherit;
            font-size: 1rem;
            resize: none;
            outline: none;
            transition: all 0.3s ease;
        }}
        
        textarea:focus {{
            border-color: var(--accent-color);
            box-shadow: 0 0 10px rgba(189, 0, 255, 0.2);
            background: rgba(255, 255, 255, 0.04);
        }}
        
        button {{
            width: 100%;
            background: linear-gradient(135deg, #bd00ff, #ff007f);
            color: #ffffff;
            border: none;
            border-radius: 12px;
            padding: 1rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            margin-top: 1.5rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(189, 0, 255, 0.3);
        }}
        
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(189, 0, 255, 0.5);
        }}
        
        button:disabled {{
            background: #4b5563;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }}
        
        .status {{
            margin-top: 1rem;
            font-size: 0.95rem;
            text-align: center;
            display: none;
        }}
        
        .success {{ color: #10b981; }}
        .error {{ color: #ef4444; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="glass-card">
            <span class="badge">{category}</span>
            <h2>{title}</h2>
            
            <div id="form-container">
                <label for="comment">✍️ Editörün Kaleminden / Görüşü:</label>
                <textarea id="comment" placeholder="Editörün kaleminden çıkmış tecrübe ve değerlendirmelerinizi buraya yazın..."></textarea>
                <button id="submit-btn" onclick="submitComment()">🚀 Onayla ve Yayınla</button>
            </div>
            
            <div id="status-msg" class="status"></div>
        </div>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        async function submitComment() {{
            const comment = document.getElementById("comment").value.trim();
            const btn = document.getElementById("submit-btn");
            const statusDiv = document.getElementById("status-msg");
            
            if (!comment) {{
                alert("Lütfen görüşünüzü yazın.");
                return;
            }}
            
            btn.disabled = true;
            btn.innerText = "⏳ Yayınlanıyor...";
            
            // Onay alındığı mesajını hemen göster
            statusDiv.className = "status success";
            statusDiv.innerHTML = "⏳ <b>Görüşünüz Alındı!</b><br>İşleminiz arka planda tamamlanacaktır, dilerseniz bu pencereyi kapatabilirsiniz.";
            statusDiv.style.display = "block";
            
            try {{
                const response = await fetch("/api/webhook", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{
                        action: "publish_draft",
                        draft_id: "{draft_id}",
                        comment: comment,
                        message_id: new URLSearchParams(window.location.search).get("message_id")
                    }})
                }});
                
                const result = await response.json();
                
                if (response.ok && result.status === "success") {{
                    statusDiv.className = "status success";
                    statusDiv.innerHTML = "🎉 <b>Haber Başarıyla Yayına Alındı!</b><br>Bu pencere otomatik kapatılıyor...";
                    statusDiv.style.display = "block";
                    
                    setTimeout(() => {{
                        tg.close();
                    }}, 2000);
                }} else {{
                    throw new Error(result.error || "Sunucu hatası oluştu.");
                }}
            }} catch (err) {{
                btn.disabled = false;
                btn.innerText = "🚀 Onayla ve Yayınla";
                statusDiv.className = "status error";
                statusDiv.innerText = "❌ Hata: " + err.message;
                statusDiv.style.display = "block";
            }}
        }}
    </script>
</body>
</html>
"""
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_page.encode('utf-8'))
            return
        
        # Simple markdown to HTML conversion
        html_content = content
        html_content = re.sub(r'^##\s+(.*?)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^###\s+(.*?)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^>\s+💬\s+(.*?)$', r'<div class="technician-note">💬 \1</div>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^>\s+(.*?)$', r'<blockquote>\1</blockquote>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
        html_content = re.sub(r'`(.*?)`', r'<code>\1</code>', html_content)
        html_content = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank">\1</a>', html_content)
        
        paragraphs = html_content.split('\n\n')
        html_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if p:
                if p.startswith('<h') or p.startswith('<div') or p.startswith('<blockquote'):
                    html_paragraphs.append(p)
                else:
                    html_paragraphs.append(f"<p>{p.replace(chr(10), '<br>')}</p>")
        final_content_html = "\n".join(html_paragraphs)
        
        cat_colors = {
            "PLC": "#00f0ff",
            "PC": "#39ff14",
            "ENDUSTRIYEL-MAKINALAR": "#ff007f",
            "OYUN": "#f857a6",
            "YAPAY-ZEKA": "#bd00ff",
            "AKILLI-EV": "#ffb703"
        }
        accent_color = cat_colors.get(category, "#e4e4e7")
        
        from datetime import timezone, timedelta
        tr_tz = timezone(timedelta(hours=3))
        
        html_page = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Taslak Önizleme: {title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #03001e;
            --accent-color: {accent_color};
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.08);
            --shadow-glow: 0 0 25px rgba(189, 0, 255, 0.15);
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background: radial-gradient(circle at 50% 0%, #11002e, var(--bg-color)) no-repeat;
            background-attachment: fixed;
            color: var(--text-color);
            font-family: 'Outfit', sans-serif;
            line-height: 1.7;
            padding: 2rem 1rem;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 780px;
            margin: 0 auto;
        }}
        
        .glass-card {{
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 2.5rem;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), var(--shadow-glow);
            transition: all 0.3s ease;
        }}
        
        .badge {{
            display: inline-block;
            color: var(--accent-color);
            border: 1px solid var(--accent-color);
            background: rgba(255, 255, 255, 0.02);
            padding: 0.4rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            margin-bottom: 1.5rem;
            text-transform: uppercase;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.02);
        }}
        
        h1 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.25;
            margin-bottom: 1.2rem;
            color: #ffffff;
            letter-spacing: -0.02em;
            text-shadow: 0 2px 10px rgba(0,0,0,0.5);
        }}
        
        .meta-info {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border-bottom: 1px solid var(--glass-border);
            padding-bottom: 1rem;
        }}
        
        .meta-info a {{
            color: var(--accent-color);
            text-decoration: none;
            transition: opacity 0.2s;
        }}
        .meta-info a:hover {{
            opacity: 0.8;
            text-decoration: underline;
        }}
        
        .description {{
            font-size: 1.15rem;
            color: #e5e7eb;
            font-weight: 300;
            margin-bottom: 2rem;
            padding-left: 1.2rem;
            border-left: 3px solid var(--accent-color);
            line-height: 1.6;
        }}
        
        .article-content {{
            font-size: 1.05rem;
            color: #f3f4f6;
            margin-bottom: 2rem;
        }}
        
        .article-content p {{
            margin-bottom: 1.5rem;
        }}
        
        .article-content h2 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.6rem;
            color: #ffffff;
            margin-top: 2.5rem;
            margin-bottom: 1rem;
            font-weight: 700;
        }}
        
        .article-content h3 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.3rem;
            color: #ffffff;
            margin-top: 2rem;
            margin-bottom: 0.8rem;
            font-weight: 700;
        }}
        
        .technician-note {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            border-left: 4px solid var(--accent-color);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 2rem 0;
            font-style: italic;
            font-weight: 300;
            color: #f9fafb;
        }}
        
        blockquote {{
            border-left: 3px solid var(--text-muted);
            padding-left: 1rem;
            font-style: italic;
            color: var(--text-muted);
            margin: 1.5rem 0;
        }}
        
        code {{
            background: rgba(255, 255, 255, 0.08);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
            color: var(--accent-color);
        }}
        
        .article-content a {{
            color: var(--accent-color);
            text-decoration: none;
            border-bottom: 1px dashed var(--accent-color);
            transition: all 0.2s;
        }}
        
        .article-content a:hover {{
            color: #ffffff;
            border-bottom: 1px solid #ffffff;
        }}
        
        .footer {{
            margin-top: 2rem;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="glass-card">
            <span class="badge">{category}</span>
            <h1>{title}</h1>
            
            <div class="meta-info">
                <span>📰 Kaynak: <a href="{source_url}" target="_blank">{source_name}</a></span>
                <span>⏱️ Durum: Yayın Onayı Bekliyor</span>
            </div>
            
            <div class="description">
                {description}
            </div>
            
            <div class="article-content">
                {final_content_html}
            </div>
        </div>
        
        <div class="footer">
            <p>AIHABERLER Editör Panel Önizleme Sistemi • {datetime.now(tr_tz).strftime('%Y')}</p>
        </div>
    </div>
</body>
</html>
"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_page.encode('utf-8'))

    def do_POST(self):
        """Processes incoming Telegram Webhook and WebApp post requests."""
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
            
        # 0. Check if this is a custom WebApp publishing POST request
        action = update.get("action")
        if action == "publish_draft":
            draft_id = update.get("draft_id")
            user_comment = update.get("comment", "").strip()
            web_message_id = update.get("message_id")
            
            if not draft_id or not user_comment:
                self.wfile.write(json.dumps({"status": "error", "error": "Geçersiz parametreler. draft_id ve comment alanları zorunludur."}).encode())
                return
                
            try:
                db = init_firebase()
                doc_ref = db.collection("pending_posts").document(draft_id)
                doc = doc_ref.get()
                if not doc.exists:
                    self.wfile.write(json.dumps({"status": "error", "error": "Taslak haber bulunamadı veya zaten yayınlandı/silindi."}).encode())
                    return
                    
                draft_data = doc.to_dict()
                if draft_data.get("status") in ["published", "queued_for_publish"]:
                    self.wfile.write(json.dumps({"status": "error", "error": "Bu haber zaten yayınlanmış veya sıraya alınmış."}).encode())
                    return
                    
                category = draft_data.get("category", "pc")
                
                # 1. Update status to queued_for_publish immediately so it disappears from pending lists
                doc_ref.update({
                    "status": "queued_for_publish",
                    "user_comment": user_comment,
                    "approved_at": time.time()
                })
                
                # 2. Update the original Telegram notification message immediately
                telegram_message_id = draft_data.get("telegram_message_id")
                
                success_text = (
                    "✍️ <b>Görüşünüz Alındı ve Yayın Sırasına Eklendi!</b>\n\n"
                    f"<b>Başlık:</b> {html.escape(draft_data['title'])}\n"
                    f"<b>Kategori:</b> {category.upper()}\n\n"
                    f"<b>Editörün Görüşü:</b> <i>{html.escape(user_comment)}</i>\n\n"
                    "Haber yayın sırasına alındı. Bir sonraki otomatik tarama/derleme çalışmasında (en geç 30 dakika içinde) toplu olarak yayına alınacaktır."
                )
                
                if telegram_message_id:
                    try:
                        edit_message_text(success_text + " Bu pencereyi kapatabilirsiniz.", telegram_message_id)
                    except Exception as e:
                        print(f"Error editing original telegram message: {e}")
                        
                if web_message_id and str(web_message_id) != str(telegram_message_id):
                    success_text_detail = success_text + "\n\nBu pencereyi kapatıp, aşağıdaki butondan listeye geri dönebilirsiniz."
                    keyboard_detail = {
                        "inline_keyboard": [
                            [{"text": "🔙 Bekleyenler Listesine Dön", "callback_data": "menu:bekleyenler"}]
                        ]
                    }
                    try:
                        edit_message_text(success_text_detail, web_message_id, reply_markup=keyboard_detail)
                    except Exception as e:
                        print(f"Error editing webapp-origin telegram message: {e}")
                        
                send_message(f"✍️ <b>{html.escape(draft_data['title'])}</b> haberi için görüşünüz alındı ve yayın sırasına eklendi!")
                self.wfile.write(json.dumps({"status": "success"}).encode())
                
            except Exception as e:
                import traceback
                print(f"Error queueing draft via WebApp: {e}\n{traceback.format_exc()}")
                self.wfile.write(json.dumps({"status": "error", "error": f"Kritik hata oluştu: {str(e)}"}).encode())
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
            
        # Reply-to-message control for pending post comment approval
        reply_to = message.get("reply_to_message")
        if reply_to:
            reply_msg_id = reply_to.get("message_id")
            db = init_firebase()
            pending_query = db.collection("pending_posts").where("telegram_message_id", "==", reply_msg_id).where("status", "==", "pending_approval").limit(1).get()
            
            if pending_query:
                # Eşleşen taslak bulundu!
                draft_doc = pending_query[0]
                doc_id = draft_doc.id
                draft_data = draft_doc.to_dict()
                
                # Kullanıcının yazdığı yorum
                user_comment = text
                category = draft_data.get("category", "pc")
                
                # 1. Update status to queued_for_publish immediately
                draft_doc.reference.update({
                    "status": "queued_for_publish",
                    "user_comment": user_comment,
                    "approved_at": time.time()
                })
                
                # 2. Update the original Telegram notification message immediately
                success_text = (
                    "✍️ <b>Görüşünüz Alındı ve Yayın Sırasına Eklendi!</b>\n\n"
                    f"<b>Başlık:</b> {html.escape(draft_data['title'])}\n"
                    f"<b>Kategori:</b> {category.upper()}\n\n"
                    f"<b>Editörün Görüşü:</b> <i>{html.escape(user_comment)}</i>\n\n"
                    "Haber yayın sırasına alındı. Bir sonraki otomatik tarama/derleme çalışmasında (en geç 20-30 dakika içinde) toplu olarak yayına alınacaktır."
                )
                try:
                    edit_message_text(success_text, reply_msg_id)
                except Exception as e:
                    print(f"Error editing original telegram message: {e}")
                    
                send_message(f"✍️ <b>{html.escape(draft_data['title'])}</b> haberi için görüşünüz alındı ve yayın sırasına eklendi!")
                self.wfile.write(json.dumps({"status": "processed"}).encode())
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
                send_message(
                    "🧹 <b>Otonom Haber Temizlik Sistemi Kaldırılmıştır</b>\n\n"
                    "Artık tüm haberler sizin onayınız ve editoryal görüşünüz eklenmeden (Telegram yorumu) yayına alınmadığı için otonom silme sistemine ihtiyaç kalmamıştır."
                )
                
            elif text == "/sil":
                send_date_selection_menu()
                
            elif text in ["/bekleyenler", "/bekleyen"]:
                send_pending_posts_list_message(user_id)
                
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
