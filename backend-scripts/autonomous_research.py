# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import time
import traceback
from datetime import datetime, timezone, timedelta

# Emojilerin Windows terminalde düzgün yazdırılabilmesi için
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Çalışma dizini ayarları
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from dotenv import load_dotenv
load_dotenv(override=True)

import firebase_helper
import ai_writer
from telegram_notifier import send_error, send_success
from google.genai import types

TR_TZ = timezone(timedelta(hours=3))

def get_recent_news_titles(max_hours=24):
    """
    web-portal/src/content/blog dizinindeki son max_hours saat içinde yayınlanan
    haberlerin başlıklarını çeker. Eğer son max_hours saatte hiç haber bulunamazsa,
    ilham almak için en son eklenen 5 haberin başlığını çeker.
    """
    blog_dir = os.path.abspath(os.path.join(base_dir, "../web-portal/src/content/blog"))
    if not os.path.exists(blog_dir):
        print(f"Hata: Blog dizini bulunamadı: {blog_dir}")
        return []

    md_files = [f for f in os.listdir(blog_dir) if f.endswith(".md")]
    recent_news = []
    all_news = []

    now = datetime.now(TR_TZ)
    cutoff = now - timedelta(hours=max_hours)

    for f_name in md_files:
        f_path = os.path.join(blog_dir, f_name)
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                content = f.read(1500) # Sadece frontmatter'ı okumak yeterli

            title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
            pub_match = re.search(r'^pubDate:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)

            if title_match and pub_match:
                title = title_match.group(1).strip()
                pub_val = pub_match.group(1).strip()
                
                # pubDate parsing
                # Örnek: 2026-06-09T16:30:00 veya 2026-06-09T16:30:00+03:00
                pub_dt = None
                try:
                    pub_dt = datetime.fromisoformat(pub_val)
                except ValueError:
                    # Alternatif format denemesi
                    try:
                        pub_dt = datetime.strptime(pub_val[:19], "%Y-%m-%dT%H:%M:%S")
                        pub_dt = pub_dt.replace(tzinfo=TR_TZ)
                    except Exception:
                        pass
                
                if pub_dt:
                    # Timezone naive ise TR_TZ ekle
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=TR_TZ)
                    
                    news_item = {"title": title, "pubDate": pub_dt}
                    all_news.append(news_item)
                    if pub_dt >= cutoff:
                        recent_news.append(news_item)
        except Exception as e:
            print(f"Hata: {f_name} dosyası okunamadı: {e}")

    # Son 24 saatte haber varsa onları başlık olarak dön
    if recent_news:
        print(f"Bilgi: Son {max_hours} saatte yayınlanmış {len(recent_news)} haber başlığı ilham kaynağı olarak seçildi.")
        return [item["title"] for item in recent_news]
    
    # Yoksa en yeni 5 haberi al
    if all_news:
        all_news.sort(key=lambda x: x["pubDate"], reverse=True)
        fallback_news = all_news[:5]
        print(f"Bilgi: Son {max_hours} saatte hiç haber bulunamadı. Son eklenen {len(fallback_news)} haber ilham kaynağı olarak seçildi.")
        return [item["title"] for item in fallback_news]

    return []

def generate_research_topics_with_gemini(inspiration_titles, max_topics=2):
    """
    Verilen haber başlıklarından ilham alarak Gemini 2.5 Flash ile
    belirtilen adette derinlemesine araştırma konusu üretir.
    """
    prompt = f"""
Sen son derece uzman, PLC sistemleri, endüstriyel otomasyon, makine tamiri ve elektrik-elektronik donanımları alanında sahadan gelen geniş tecrübelere sahip kıdemli bir elektronik teknisyeni ve teknik editörsün.
Aşağıda, portalımızda son yayınlanan haberlerin başlıkları listelenmiştir:
{json.dumps(inspiration_titles, ensure_ascii=False, indent=2)}

GÖREVİN:
Bu haber başlıklarını analiz et. Bu konulardan ilham alarak ama onlarla doğrudan aynı gelişmeyi ele almayan, tamamen yeni, bağımsız, güncel ve Google Arama ile derinlemesine araştırılıp 4 paragraflık kapsamlı makaleler yazılabilecek maksimum {max_topics} adet otonom araştırma konusu üret.

YAYIN POLİTİKASI VEYA KATEGORİ KURALLARI:
1. Konuların kategorisi sadece şu altısından biri olmalıdır: "plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka", "akilli-ev".
2. Suya sabuna dokunmayan, yasal riski sıfır, siyaset dışı, magazin dışı, borsa/yatırım/fiyat spekülasyonu içermeyen, tamamen nesnel, otomasyon, bilgisayar teknolojileri, elektrik, oyun dünyası, PLC kontrolörler, motor sürücüler, pratik cihaz donanımları, akıllı ev otomasyonları (IoT) veya tamir çözümleri odaklı teknik konular olmalıdır.
3. Her konu için:
   - `title`: Sürükleyici, profesyonel, clickbait olmayan merak uyandırıcı Türkçe bir haber başlığı.
   - `query`: Bu konunun detaylarını Google Arama ile araştırmak için kullanılacak İngilizce net ve nokta atışı bir arama sorgusu (Örn: "Siemens S7-1500 firmware updates plc", "robot vacuum lidar sensor repair smart home", "industrial assembly line cnc troubleshooting").
   - `category`: "plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka" veya "akilli-ev" değerlerinden biri.

Çıktıyı kesinlikle aşağıdaki JSON formatında ver (başka açıklama ekleme, markdown kod bloğu içinde olmalıdır):
```json
{{
  "topics": [
    {{
      "title": "...",
      "query": "...",
      "category": "..."
    }}
  ]
}}
```
"""
    max_retries = len(ai_writer.API_KEYS) if ai_writer.API_KEYS else 3
    last_error = "Gemini ile fikir üretilemedi."

    for attempt in range(max_retries):
        client = ai_writer.get_next_client()
        try:
            print(f"Gemini ile otonom araştırma fikirleri üretiliyor (Deneme {attempt + 1}/{max_retries})...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text.strip())
            topics = data.get("topics", [])
            
            # Kategori ve veri kontrolü
            valid_topics = []
            ALLOWED_CATEGORIES = {"plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka", "akilli-ev"}
            for t in topics:
                title = t.get("title")
                query = t.get("query")
                category = t.get("category", "").strip().lower()
                
                if category not in ALLOWED_CATEGORIES:
                    category = "pc"
                
                if title and query:
                    valid_topics.append({
                        "title": title.strip(),
                        "query": query.strip(),
                        "category": category
                    })
            
            print(f"Üretilen otonom araştırma konuları: {valid_topics}")
            return valid_topics
        except Exception as e:
            last_error = str(e)
            print(f"Hata (Gemini Fikir Üretimi): {last_error}")
            ai_writer.rotate_key()
            
    print(f"HATA: Otonom araştırma konuları üretilemedi. Detay: {last_error}")
    return []

def run_autonomous_research(force=False):
    """
    Otonom araştırma akışını çalıştırır.
    """
    print("Otonom haber araştırması süreci başlatılıyor...")
    
    # 1. Firestore Ayarlarını Oku
    try:
        config = firebase_helper.get_research_config()
    except Exception as fs_err:
        print(f"Firestore otonom araştırma ayarları okunamadı: {fs_err}")
        if not force:
            sys.exit(1)
        # Fallback varsayılanlar
        config = {
            "is_active": True,
            "interval_hours": 24,
            "last_run_time": 0.0,
            "is_running": False
        }

    is_active = config.get("is_active", True)
    interval_hours = config.get("interval_hours", 24)
    last_run_time = config.get("last_run_time", 0.0)
    is_running = config.get("is_running", False)
    inspiration_hours = config.get("inspiration_hours", 24)
    max_topics = config.get("max_topics", 2)

    now = time.time()
    elapsed_hours = (now - last_run_time) / 3600.0

    if not force:
        # Zamanlayıcı aktiflik kontrolü
        if not is_active:
            print("Bulut otonom araştırma devre dışı (Durdurulmuş). Akış sonlandırılıyor.")
            sys.exit(0)
            
        # Süre kontrolü
        if elapsed_hours < interval_hours:
            remaining = int(interval_hours - elapsed_hours)
            print(f"Otonom araştırma için henüz süre dolmadı. Kalan: {remaining} saat. Akış sonlandırılıyor.")
            sys.exit(0)
            
        # Mükerrer çalışma (lock) kontrolü
        # 30 dakikadan uzun süredir kilitliyse kilidi yok say
        if is_running and elapsed_hours < 0.5:
            print("Başka bir otonom araştırma işlemi şu anda aktif. Çakışmayı önlemek için sonlandırılıyor.")
            sys.exit(0)

    # 2. Kilidi Aktif Et
    try:
        firebase_helper.update_research_config(is_running=True)
    except Exception as e:
        print(f"Firestore kilitleme hatası: {e}")

    success_news = []
    failed_news = []
    
    try:
        # API hata listesini temizle
        ai_writer.FAILED_KEYS_THIS_RUN = []

        # 3. Son Haber Başlıklarını Çek
        inspiration_titles = get_recent_news_titles(max_hours=inspiration_hours)
        if not inspiration_titles:
            print("İlham alınacak hiçbir haber bulunamadı. Akış sonlandırılıyor.")
            firebase_helper.update_research_config(is_running=False, last_run_time=time.time())
            sys.exit(0)

        # 4. Gemini ile Konuları Belirle
        topics = generate_research_topics_with_gemini(inspiration_titles, max_topics=max_topics)
        if not topics:
            raise ValueError("Gemini otonom araştırma konusu üretemedi.")

        # 5. Haberleri Araştır, Yaz ve Kaydet
        # config.json'dan kaydetme dizinlerini yükle
        from fetcher import load_config
        app_config = load_config()
        output_dir = app_config["settings"]["output_dir"]
        images_dir = app_config["settings"]["images_dir"]
        
        abs_output_dir = os.path.abspath(os.path.join(base_dir, output_dir))
        abs_images_dir = os.path.abspath(os.path.join(base_dir, images_dir))

        for item in topics:
            title = item["title"]
            query = item["query"]
            category = item["category"]
            
            print(f"\n🔍 Otonom Araştırma Başlıyor: '{title}' (Arama Sorgusu: '{query}')")
            try:
                # Google Search Grounding ile makale yazdır
                news_data = ai_writer.research_topic_with_gemini(query)
                if not news_data:
                    raise ValueError("Google Arama Grounding ile veri üretilemedi.")
                
                # Başlık ve kategoriyi fikir belirleme aşamasından gelen değerlerle güncelle/sabitle
                news_data["title"] = title
                news_data["category"] = category
                
                # Otonom araştırma makalesini Astro formatında kaydet (TASLAK OLARAK)
                draft_post = ai_writer.save_news_as_markdown(
                    news_data,
                    abs_output_dir,
                    abs_images_dir,
                    "Otonom Araştırma (AI)",
                    "https://aihaberler.web.app",
                    draft_only=True
                )
                
                # Mükerrer haber kontrolü (Otonom araştırma için)
                draft_url = draft_post.get("sourceUrl")
                if draft_url and not (
                    "aihaberler.web.app" in draft_url.lower() 
                    or "ai-haber-portali.vercel.app" in draft_url.lower() 
                    or "localhost" in draft_url.lower()
                ):
                    db = firebase_helper.init_firebase()
                    all_drafts = db.collection("pending_posts").stream()
                    existing_urls = set()
                    for d in all_drafts:
                        url_val = d.to_dict().get("sourceUrl")
                        if url_val:
                            existing_urls.add(url_val)
                            
                    from fetcher import get_all_published_urls
                    published_urls = get_all_published_urls()
                    
                    if draft_url in existing_urls or draft_url in published_urls:
                        print(f"⚠️ Otonom Araştırma Geçildi: '{title}' haberi ({draft_url}) zaten mevcut veya onay bekliyor.")
                        continue
                
                # Firestore'a ekle ve Telegram onayı gönder
                db = firebase_helper.init_firebase()
                pending_ref = db.collection("pending_posts").document()
                p_doc_id = pending_ref.id
                
                from telegram_notifier import send_pending_post_notification
                msg_id = send_pending_post_notification(
                    title=draft_post["title"],
                    summary=draft_post["description"],
                    category=draft_post["category"],
                    doc_id=p_doc_id
                )
                
                draft_post["id"] = p_doc_id
                draft_post["telegram_message_id"] = msg_id
                draft_post["status"] = "pending_approval"
                draft_post["created_at"] = time.time()
                
                pending_ref.set(draft_post)
                
                success_news.append((title, "taslak"))
                print(f"✅ Otonom araştırma taslağı başarıyla oluşturuldu: '{title}'")
            except Exception as item_err:
                err_msg = str(item_err)
                print(f"❌ '{title}' konusu araştırılırken hata: {err_msg}")
                failed_news.append((title, err_msg))

        print(f"\nOtonom Araştırma Akışı Tamamlandı. Başarılı: {len(success_news)}, Başarısız: {len(failed_news)}")

    except Exception as main_err:
        err_msg = f"Otonom araştırma sırasında kritik hata: {main_err}\n{traceback.format_exc()}"
        print(err_msg)
        send_error("Otonom Araştırma Kritik Hatası", err_msg)
        try:
            firebase_helper.update_research_config(is_running=False)
        except:
            pass
        sys.exit(1)

    # 6. Sonuçları Kaydet ve Kilidi Kaldır
    try:
        # İndeksi yeniden oluştur
        import main
        main.rebuild_posts_index_locally()
    except Exception as idx_err:
        print(f"İndeks güncellenemedi: {idx_err}")

    try:
        firebase_helper.update_research_config(last_run_time=time.time(), is_running=False)
    except Exception as fs_up_err:
        print(f"Firestore son çalışma saati güncellenemedi: {fs_up_err}")

    # 7. Telegram Bildirimi
    report_msg = ""
    if success_news:
        success_details = "\n".join([f"- <b>{t}</b> (Yayın Onayı Bekliyor)" for t, s in success_news])
        report_msg += f"🧠 <b>Onay Bekleyen Otonom Araştırma Taslakları ({len(success_news)} adet):</b>\n{success_details}\n\n"
        
    if failed_news:
        failed_details = "\n".join([f"- <b>{t}</b>: {d}" for t, d in failed_news])
        report_msg += f"❌ <b>Başarısız Olan Otonom Araştırmalar ({len(failed_news)} adet):</b>\n{failed_details}\n\n"
        
    if ai_writer.FAILED_KEYS_THIS_RUN:
        keys_details = "\n".join([f"- 🔑 <code>{k}</code>: {err[:60]}..." for k, err in ai_writer.FAILED_KEYS_THIS_RUN])
        report_msg += f"⚠️ <b>Hata Alan API Anahtarları (Sondan 6 Hane):</b>\n{keys_details}\n\n"
        
    if report_msg:
        report_msg += "🔗 <b>Canlı Haber Sitesi:</b> <a href='https://aihaberler.web.app'>aihaberler.web.app</a>\n"
        if failed_news:
            send_error("Otonom Araştırma Akışı - Rapor", report_msg)
        else:
            send_success("Otonom Araştırma Akışı - Başarılı!", report_msg)

if __name__ == "__main__":
    force_run = "--force" in sys.argv
    run_autonomous_research(force=force_run)
