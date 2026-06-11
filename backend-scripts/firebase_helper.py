import os
import json
import time
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Ortam değişkenlerini yükle
load_dotenv(override=True)

db_client = None

def init_firebase():
    """Firebase Admin SDK'yı başlatır ve Firestore client'ı döner."""
    global db_client
    if db_client is not None:
        return db_client

    # Zaten başlatılmış mı kontrol et
    try:
        app = firebase_admin.get_app()
    except ValueError:
        # Başlatılmamış, şimdi başlatacağız
        cred_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firebase_credentials.json")
        cred_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

        if os.path.exists(cred_file):
            print("Firebase yerel credential dosyası ile başlatılıyor...")
            cred = credentials.Certificate(cred_file)
            firebase_admin.initialize_app(cred)
        elif cred_env:
            print("Firebase ortam değişkeni (JSON) ile başlatılıyor...")
            try:
                cred_dict = json.loads(cred_env)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"HATA: Ortam değişkenindeki FIREBASE_SERVICE_ACCOUNT_JSON ayrıştırılamadı: {e}")
                # Kimlik bilgisi olmadan varsayılan kimlik bilgileriyle (Application Default Credentials) dene
                firebase_admin.initialize_app()
        else:
            print("BİLGİ: Firebase kimlik belgesi bulunamadı. Application Default Credentials ile deneniyor...")
            # Bu mod yerel CLI yetkilendirmesi varsa veya GCP ortamlarındaysak çalışır
            firebase_admin.initialize_app()

    db_client = firestore.client()
    return db_client

def get_scheduler_config():
    """Firestore'dan zamanlayıcı ayarlarını çeker. Yoksa varsayılan oluşturur."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("scheduler")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        # Eksik alanlar varsa varsayılanla tamamla
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
        # Varsayılan konfigürasyonu Firestore'a yaz ve dön
        default_config = {
            "interval_minutes": 20,
            "last_run_time": time.time(),
            "is_running": False,
            "is_active": True
        }
        doc_ref.set(default_config)
        print("Firestore üzerinde varsayılan zamanlayıcı ayarları oluşturuldu.")
        return default_config
 
def update_scheduler_config(interval_minutes=None, last_run_time=None, is_running=None, is_active=None):
    """Firestore'daki zamanlayıcı ayarlarını günceller."""
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
        print(f"Firestore zamanlayıcı ayarları güncellendi: {update_data}")

def get_cleanup_config():
    """Firestore'dan otonom temizlik ayarlarını çeker. Yoksa varsayılan oluşturur."""
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
        print("Firestore üzerinde varsayılan otonom temizlik ayarları oluşturuldu.")
        return default_config

def update_cleanup_config(interval_hours=None, last_cleanup_time=None, is_active=None):
    """Firestore'daki otonom temizlik ayarlarını günceller."""
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
        # Document might not exist if update is called before get, so use set(..., merge=True)
        doc_ref.set(update_data, merge=True)
        print(f"Firestore otonom temizlik ayarları güncellendi: {update_data}")

def get_publish_timer_config():
    """Firestore'dan yayına alma zamanlayıcı ayarlarını çeker. Yoksa varsayılan oluşturur."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("publish_timer")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        return {
            "delay_minutes": int(data.get("delay_minutes", 0)),
            "timer_start_time": float(data.get("timer_start_time", 0.0)),
            "next_publish_time": float(data.get("next_publish_time", 0.0))
        }
    else:
        default_config = {
            "delay_minutes": 0,
            "timer_start_time": 0.0,
            "next_publish_time": 0.0
        }
        doc_ref.set(default_config)
        print("Firestore üzerinde varsayılan yayına alma zamanlayıcı ayarları oluşturuldu.")
        return default_config

def update_publish_timer_config(delay_minutes=None, timer_start_time=None, next_publish_time=None):
    """Firestore'daki yayına alma zamanlayıcı ayarlarını günceller."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("publish_timer")
    
    update_data = {}
    if delay_minutes is not None:
        update_data["delay_minutes"] = int(delay_minutes)
    if timer_start_time is not None:
        update_data["timer_start_time"] = float(timer_start_time)
    if next_publish_time is not None:
        update_data["next_publish_time"] = float(next_publish_time)
        
    if update_data:
        doc_ref.set(update_data, merge=True)
        print(f"Firestore yayına alma zamanlayıcı ayarları güncellendi: {update_data}")

def get_rss_sources():
    """Firestore'dan RSS kaynaklarını çeker. Boşsa yerel config.json'dan göç (migration) yapar."""
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
        
    if not sources:
        # Firestore boş, config.json'dan göç yap
        print("BİLGİ: Firestore 'rss_sources' koleksiyonu boş. Yerel config.json'dan veriler aktarılıyor...")
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    default_sources = config_data.get("sources", [])
                    for src in default_sources:
                        name = src.get("name")
                        doc_id = "".join(c for c in name.lower() if c.isalnum() or c == "_")
                        sources_ref.document(doc_id).set(src)
                        sources.append(src)
                print(f"Başarıyla {len(sources)} adet RSS kaynağı buluta aktarıldı.")
            except Exception as e:
                print(f"HATA: Yerel config.json'dan göç yapılamadı: {e}")
    return sources

def add_rss_source(name, url, category):
    """Yeni bir RSS kaynağını Firestore'a ekler."""
    db = init_firebase()
    doc_id = "".join(c for c in name.lower() if c.isalnum() or c == "_")
    doc_ref = db.collection("rss_sources").document(doc_id)
    doc_ref.set({
        "name": name,
        "url": url,
        "category": category
    })
    print(f"Firestore RSS kaynağı eklendi: {name} ({url}) [{category}]")
    return True

def delete_rss_source(name):
    """Firestore'dan belirtilen isimdeki RSS kaynağını siler."""
    db = init_firebase()
    doc_id = "".join(c for c in name.lower() if c.isalnum() or c == "_")
    doc_ref = db.collection("rss_sources").document(doc_id)
    if doc_ref.get().exists:
        doc_ref.delete()
        print(f"Firestore RSS kaynağı silindi: {name}")
        return True
    print(f"HATA: Firestore üzerinde '{name}' isminde kaynak bulunamadı.")
    return False

def add_custom_request(topic):
    """Kullanıcının özel haber talebini Firestore kuyruğuna ekler."""
    db = init_firebase()
    doc_ref = db.collection("custom_requests").document()
    doc_ref.set({
        "topic": topic,
        "status": "pending",
        "requested_at": time.time()
    })
    print(f"Firestore özel haber talebi kuyruğa eklendi: {topic}")
    return True

def get_pending_custom_requests():
    """Firestore'dan beklemedeki özel haber taleplerini çeker."""
    db = init_firebase()
    requests_ref = db.collection("custom_requests")
    # Composite index hatasını önlemek için sıralamayı Python tarafında yapıyoruz
    query = requests_ref.where("status", "==", "pending").stream()
    
    requests_list = []
    for doc in query:
        data = doc.to_dict()
        data["id"] = doc.id
        requests_list.append(data)
        
    # Python tarafında requested_at alanına göre sırala
    requests_list.sort(key=lambda x: x.get("requested_at", 0))
    return requests_list

def mark_custom_request_completed(doc_id):
    """Firestore'daki özel haber talebinin durumunu tamamlandı olarak günceller."""
    db = init_firebase()
    doc_ref = db.collection("custom_requests").document(doc_id)
    doc_ref.update({
        "status": "completed",
        "completed_at": time.time()
    })
    print(f"Firestore özel haber talebi tamamlandı olarak işaretlendi: {doc_id}")
    return True

# === KATMAN 1: Link Bazlı Kalıcı Kara Liste ===
# In-memory cache to avoid repeated Firestore reads within the same pipeline run
_blacklist_cache = None

def get_blacklisted_links():
    """Firestore'dan kalıcı kara listeyi çeker. 30 günden eski olanları otomatik temizler."""
    global _blacklist_cache
    if _blacklist_cache is not None:
        return _blacklist_cache
    
    db = init_firebase()
    doc_ref = db.collection("system_config").document("blacklisted_links")
    doc = doc_ref.get()
    
    now = time.time()
    cutoff_time = now - (30 * 24 * 3600)  # 30 gün öncesi (30 gün * 24 saat * 3600 saniye)
    
    dirty = False
    active_links = {}
    
    if doc.exists:
        data = doc.to_dict()
        links_data = data.get("links", {})
        
        # Geriye uyumluluk: Eğer eski veri tipi list (array) ise Map formatına dönüştür
        if isinstance(links_data, list):
            print("BİLGİ: Eski liste formatındaki kara liste Map formatına dönüştürülüyor...")
            links_data = {link: now for link in links_data}
            dirty = True
            
        # 30 günden eski olanları temizle
        if isinstance(links_data, dict):
            for link, added_time in links_data.items():
                if added_time >= cutoff_time:
                    active_links[link] = added_time
                else:
                    dirty = True
    else:
        # İlk çalışma: boş döküman oluştur
        doc_ref.set({"links": {}, "last_updated": now})
        _blacklist_cache = set()
        print("Firestore üzerinde kara liste dökümanı oluşturuldu (system_config/blacklisted_links).")
        return _blacklist_cache
        
    if dirty:
        # Güncellenmiş aktif listeyi kaydet
        doc_ref.set({
            "links": active_links,
            "last_updated": now
        })
        print(f"🧹 Temizlik: Kara listeden 30 günden eski olan linkler temizlendi. Aktif link sayısı: {len(active_links)}")
        
    _blacklist_cache = set(active_links.keys())
    print(f"Kara liste yüklendi: {len(_blacklist_cache)} adet aktif engellenmiş link.")
    return _blacklist_cache

def add_to_blacklist(new_links):
    """Verilen linkleri Firestore kara listesine Map formatında toplu olarak ekler."""
    global _blacklist_cache
    if not new_links:
        return
    
    db = init_firebase()
    doc_ref = db.collection("system_config").document("blacklisted_links")
    
    # Cache ve aktif listeyi yükle
    get_blacklisted_links()
    
    now = time.time()
    
    # Güncel dökümanı oku
    doc = doc_ref.get()
    current_links = {}
    if doc.exists:
        data = doc.to_dict()
        links_data = data.get("links", {})
        if isinstance(links_data, dict):
            current_links = links_data
            
    # Sadece yeni olanları ekle
    added_count = 0
    for link in new_links:
        if link not in current_links:
            current_links[link] = now
            added_count += 1
            
    if added_count > 0:
        doc_ref.set({
            "links": current_links,
            "last_updated": now
        })
        # Cache'i güncelle
        _blacklist_cache = set(current_links.keys())
        print(f"Kara listeye {added_count} yeni link eklendi. Toplam aktif: {len(_blacklist_cache)}")

def get_research_config():
    """Firestore'dan otonom araştırma ayarlarını çeker. Yoksa varsayılan oluşturur."""
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
        print("Firestore üzerinde varsayılan otonom araştırma ayarları oluşturuldu.")
        return default_config

def update_research_config(interval_hours=None, last_run_time=None, is_running=None, is_active=None, inspiration_hours=None, max_topics=None):
    """Firestore'daki otonom araştırma ayarlarını günceller."""
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
        print(f"Firestore otonom araştırma ayarları güncellendi: {update_data}")

def get_pending_posts_info():
    """Queries pending_posts collection in Firestore and returns a tuple:
    (pending_titles_list, pending_source_urls_set)
    """
    db = init_firebase()
    pending_ref = db.collection("pending_posts")
    docs = pending_ref.stream()
    
    pending_titles = []
    pending_source_urls = set()
    
    for doc in docs:
        data = doc.to_dict()
        status = data.get("status")
        if status in ["pending_approval", "queued_for_deletion", "queued_for_publish", "published"]:
            title = data.get("title")
            source_url = data.get("sourceUrl")
            if title:
                pending_titles.append(title)
            if source_url:
                pending_source_urls.add(source_url)
                
    print(f"Pending/Queued posts loaded: {len(pending_titles)} titles, {len(pending_source_urls)} links.")
    return pending_titles, pending_source_urls

