import sys
import os

# Windows CP1254 terminal emoji encoding fix
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
import time
import traceback
from dotenv import load_dotenv

# Çalışma dizinini backend-scripts olarak ayarla
base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)
sys.path.append(base_dir)

load_dotenv(override=True)
from fetcher import fetch_new_news, load_config
from ai_writer import process_single_news
from telegram_notifier import send_error, send_success
import firebase_helper
import re

def rebuild_posts_index_locally():
    print("Rebuilding posts index locally from workspace files...")
    blog_dir = os.path.abspath(os.path.join(base_dir, "../web-portal/src/content/blog"))
    if not os.path.exists(blog_dir):
        print(f"Error: blog directory not found: {blog_dir}")
        return
        
    md_files = [f for f in os.listdir(blog_dir) if f.endswith(".md")]
    posts = {}
    
    for idx, f_name in enumerate(md_files, start=1):
        f_path = os.path.join(blog_dir, f_name)
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                content = f.read(1500) # Read frontmatter
                
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
                
            p_id = f"p{idx}"
            posts[p_id] = {
                "slug": f_name,
                "title": title,
                "date": pub_date,
                "pubDateTime": pub_datetime,
                "image": hero_image,
                "category": category,
                "sha": "" # SHA is empty, fetched dynamically when deleting!
            }
        except Exception as e:
            print(f"Error indexing local file {f_name}: {e}")
            
    index_data = {
        "last_updated": time.time(),
        "posts": posts
    }
    
    try:
        db = firebase_helper.init_firebase()
        db.collection("system_config").document("posts_index").set(index_data)
        print(f"Success: Local posts index successfully written to Firestore. Total indexed: {len(posts)}")
    except Exception as fs_err:
        print(f"Error saving posts index to Firestore: {fs_err}")

def process_daily_deletions():
    print("Daily deletion queue check started...")
    try:
        import firebase_helper
        from datetime import datetime, timezone, timedelta
        tr_tz = timezone(timedelta(hours=3))
        now_tr = datetime.now(tr_tz)
        current_date_str = now_tr.strftime("%Y-%m-%d")
        
        db = firebase_helper.init_firebase()
        
        # Get scheduler config to read last_deletion_date
        sched_ref = db.collection("system_config").document("scheduler")
        sched_doc = sched_ref.get()
        last_deletion_date = ""
        if sched_doc.exists:
            last_deletion_date = sched_doc.to_dict().get("last_deletion_date", "")
            
        print(f"Current TR Date: {current_date_str}, Last Deletion Date: {last_deletion_date}")
        
        # Check if we transitioned to a new day
        if last_deletion_date == current_date_str:
            print("Daily deletions already processed for today. Skipping.")
            return
            
        print(f"New day detected ({current_date_str}). Processing deletion queue...")
        
        # Fetch pending items from deletion_queue
        queue_ref = db.collection("deletion_queue")
        pending_deletions = queue_ref.where("status", "==", "pending").stream()
        
        deleted_count = 0
        for doc in pending_deletions:
            data = doc.to_dict()
            slug = data.get("slug")
            image_name = data.get("image_name")
            del_type = data.get("type", "draft")
            
            print(f"Processing deletion for slug={slug}, image={image_name}, type={del_type}")
            
            # Delete markdown file if type is published
            if del_type == "published" and slug:
                clean_slug = slug.replace(".md", "")
                md_local_path = os.path.abspath(os.path.join(base_dir, f"../web-portal/src/content/blog/{clean_slug}.md"))
                if os.path.exists(md_local_path):
                    os.remove(md_local_path)
                    print(f"Deleted markdown file: {md_local_path}")
                    
            # Delete image file if present
            if image_name:
                img_local_path = os.path.abspath(os.path.join(base_dir, f"../web-portal/public/images/news/{image_name}"))
                if os.path.exists(img_local_path):
                    os.remove(img_local_path)
                    print(f"Deleted image file: {img_local_path}")
                    
            # Delete from pending_posts if it is a draft
            if del_type == "draft" and slug:
                try:
                    pending_ref = db.collection("pending_posts")
                    drafts = pending_ref.where("slug", "==", slug).stream()
                    for d in drafts:
                        d.reference.delete()
                        print(f"Deleted draft document from pending_posts: {d.id}")
                except Exception as e:
                    print(f"Error deleting draft document from Firestore: {e}")
            
            # Update deletion_queue status
            doc.reference.update({
                "status": "processed",
                "processed_at": time.time()
            })
            deleted_count += 1
            
        print(f"Deletion queue processing completed. Total processed: {deleted_count}")
        
        # If any file was deleted, rebuild index locally
        if deleted_count > 0:
            rebuild_posts_index_locally()
            
        # Update last_deletion_date in scheduler document
        sched_ref.set({"last_deletion_date": current_date_str}, merge=True)
        print(f"Updated last_deletion_date to {current_date_str} in Firestore.")
        
    except Exception as e:
        print(f"Error processing daily deletions: {e}")
        import traceback
        traceback.print_exc()

def main():
    # 0. Günlük silme kuyruğunu çalıştır
    process_daily_deletions()

    # 1. Parametre Kontrolü
    force_run = "--force" in sys.argv
    cleanup_force = "--cleanup" in sys.argv
    research_mode = "--research" in sys.argv
    
    # 1.3. Eğer sadece otonom araştırma isteniyorsa
    if research_mode:
        print("Sadece otonom araştırma tetiklendi. RSS taraması atlanıyor.")
        try:
            from autonomous_research import run_autonomous_research
            run_autonomous_research(force=True)
        except Exception as research_err:
            import traceback
            print(f"Otonom araştırma sırasında hata oluştu: {research_err}")
            traceback.print_exc()
            send_error("Otonom Araştırma Çalıştırma Hatası", f"Hata: {research_err}\n{traceback.format_exc()}")
            sys.exit(1)
        sys.exit(0)
        
    # 1.5. Eğer sadece temizlik isteniyorsa
    if cleanup_force:
        print("Otonom temizlik sistemi devre dışı bırakılmıştır.")
        sys.exit(0)
    
    # 2. Firestore Zamanlayıcı Kontrolü
    try:
        scheduler_config = firebase_helper.get_scheduler_config()
        interval = scheduler_config["interval_minutes"]
        last_run = scheduler_config["last_run_time"]
        is_running = scheduler_config["is_running"]
        is_active = scheduler_config.get("is_active", True)
        
        now = time.time()
        elapsed_minutes = (now - last_run) / 60.0
        
        if not force_run:
            # Otonom Zamanlayıcı Aktiflik (Başlatma/Durdurma) Kontrolü
            if not is_active:
                print("Bulut otonom zamanlayıcı devre dışı (Durdurulmuş). Tarama atlanıyor.")
                sys.exit(0)
                
            # Süre kontrolü
            if elapsed_minutes < interval:
                remaining = int(interval - elapsed_minutes)
                print(f"Otonom tarama için henüz süre dolmadı. Kalan: {remaining} dakika. Akış sonlandırılıyor.")
                sys.exit(0)
                
            # Mükerrer çalışma (lock) kontrolü
            # Eğer 15 dakikadan uzun süredir kilitliyse muhtemelen kilit asılı kalmıştır, kilidi yok say
            if is_running and elapsed_minutes < 15.0:
                print("Başka bir tarama/derleme işlemi şu anda aktif. Çakışmayı önlemek için sonlandırılıyor.")
                sys.exit(0)
                
        # Kilidi aktif et
        firebase_helper.update_scheduler_config(is_running=True)
        print(f"Tarama başlatılıyor. Tetikleme: {'Manuel (--force)' if force_run else 'Otonom (Süre doldu)'}")
        
    except Exception as e:
        print(f"Firestore zamanlayıcı kontrolü başarısız oldu: {e}")
        # Hata durumunda eğer force ise devam et, değilse güvenli çıkış yap
        if not force_run:
            sys.exit(1)

    # 3. Config yükle
    try:
        config = load_config()
    except Exception as e:
        err_msg = f"Config yüklenemedi: {e}\n{traceback.format_exc()}"
        print(f"Hata: {err_msg}")
        send_error("Haber Portalı Config Hatası", err_msg)
        firebase_helper.update_scheduler_config(is_running=False)
        sys.exit(1)
        
    # 3.5 Otonom Temizlik Periyot Kontrolü kaldırıldı (manuel yönetim)
    pass
        
    # 4. Yeni haberleri çek
    try:
        new_news = fetch_new_news()
    except Exception as e:
        err_msg = f"Haberler çekilirken hata oluştu: {e}\n{traceback.format_exc()}"
        print(f"Hata: {err_msg}")
        send_error("Haber Portalı RSS Çekme Hatası", err_msg)
        firebase_helper.update_scheduler_config(is_running=False)
        sys.exit(1)

    # 4.5 Firestore'daki bekleyen özel haber taleplerini çek
    pending_requests = []
    try:
        pending_requests = firebase_helper.get_pending_custom_requests()
    except Exception as e:
        print(f"Özel haber talepleri Firestore'dan alınamadı: {e}")

    # Eğer hem yeni RSS haberi yoksa hem de bekleyen özel talep yoksa kilidi kaldır ve çık
    if not new_news and not pending_requests:
        print("İşlenecek yeni RSS haberi veya özel talep bulunamadı. Akış sonlandırılıyor.")
        try:
            rebuild_posts_index_locally()
        except Exception as idx_err:
            print(f"Error rebuilding index on dry-run: {idx_err}")
        firebase_helper.update_scheduler_config(last_run_time=time.time(), is_running=False)
        
        # Eğer kullanıcı manuel tetiklediyse bilgi mesajı gönderelim (otomatik çalışmada spam olmaması için gönderilmez)
        if force_run:
            info_msg = (
                "ℹ️ <b>Haber Tarama Raporu</b>\n\n"
                "Tarama işlemi başarıyla tamamlandı ancak <b>yayınlanacak yeni bir haber bulunamadı.</b>\n\n"
                "🔍 <b>Olası Nedenler:</b>\n"
                "• RSS kaynaklarında henüz yeni bir içerik paylaşılmamış olabilir.\n"
                "• Veya çekilen tüm aday haberler, sitemizdeki mevcut haberlerle semantik benzerlik gösterdiği için <b>Gemma 31B Semantik Filtresi</b> tarafından mükerrer kabul edilip başarıyla elenmiştir.\n\n"
                "🔗 <b>Canlı Portal:</b> <a href='https://aihaberler.web.app'>aihaberler.web.app</a>"
            )
            send_success("Haber Tarama Raporu - Yeni Haber Yok", info_msg)
            
        sys.exit(0)

        
    # 5. API Anahtarları kontrolü
    if not os.getenv("GEMINI_API_KEYS") and not os.getenv("GEMINI_API_KEY"):
        err_msg = "GEMINI_API_KEYS veya GEMINI_API_KEY ortam değişkeni tanımlı değil. Lütfen .env dosyasını kontrol edin."
        print(f"HATA: {err_msg}")
        send_error("Haber Portalı Başlatma Hatası", err_msg)
        firebase_helper.update_scheduler_config(is_running=False)
        sys.exit(1)
        
    # 6. Haberleri sırayla işle
    success_count = 0
    failed_news = []
    success_news = []
    
    # API hata listesini temizle
    import ai_writer
    ai_writer.FAILED_KEYS_THIS_RUN = []
    
    # 6.1 Önce bekleyen özel haber taleplerini işle
    if pending_requests:
        print(f"\n[{len(pending_requests)}] adet bekleyen özel haber talebi işleniyor...")
        try:
            from ai_writer import research_topic_with_gemini, save_news_as_markdown, slugify
            from telegram_notifier import send_pending_post_notification
            
            output_dir = config["settings"]["output_dir"]
            images_dir = config["settings"]["images_dir"]
            
            abs_output_dir = os.path.abspath(os.path.join(base_dir, output_dir))
            abs_images_dir = os.path.abspath(os.path.join(base_dir, images_dir))
            
            for req in pending_requests:
                topic = req["topic"]
                doc_id = req["id"]
                print(f"Özel Haber Talebi İşleniyor: '{topic}'")
                
                try:
                    # 1. Gemini Search Grounding ile araştır ve yaz
                    news_data = research_topic_with_gemini(topic)
                    if not news_data:
                        raise ValueError("Gemini araştırma sonucunda boş veri döndü.")
                        
                    # Kategori belirleme yetkisi kullanıcıdadır veya AI'ın kısıtlı tahminindedir.
                    category = req.get("category") or news_data.get("category") or "pc"
                    category = category.strip().lower()
                    
                    # Kategori koruması
                    ALLOWED_CATEGORIES = {"plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka", "akilli-ev"}
                    if category not in ALLOWED_CATEGORIES:
                        category = "pc"
                        
                    news_data["category"] = category
                    title = news_data.get("title", "Yeni Haber")
                    
                    # 2. Markdown ve Görsel olarak kaydet (TASLAK OLARAK)
                    draft_post = save_news_as_markdown(
                        news_data, 
                        abs_output_dir, 
                        abs_images_dir, 
                        "Editörün Kalemi", 
                        "https://aihaberler.web.app",
                        draft_only=True
                    )
                    
                    # Firestore'a ekle ve Telegram onayı gönder
                    db = firebase_helper.init_firebase()
                    pending_ref = db.collection("pending_posts").document()
                    p_doc_id = pending_ref.id
                    
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
                    
                    # 3. Firestore'da tamamlandı yap
                    firebase_helper.mark_custom_request_completed(doc_id)
                    
                    # 4. Raporlama
                    success_count += 1
                    success_news.append((f"[Özel Talep] {title}", "taslak"))
                    
                except Exception as e:
                    err_msg = f"Özel haber yazımı başarısız: {e}"
                    print(err_msg)
                    failed_news.append((f"[Talep] {topic}", err_msg))
                    # Hata olsa bile kuyruğu kilitlemesin, tamamlandı işaretle
                    firebase_helper.mark_custom_request_completed(doc_id)
        except Exception as e:
            print(f"Özel haber talebi işlenirken genel hata: {e}")
            
    # 6.2 RSS haberlerini işle
    
    from telegram_notifier import send_pending_post_notification
    for idx, raw_news in enumerate(new_news, start=1):
        print(f"\n[{idx}/{len(new_news)}] Haber İşleniyor...")
        try:
            success, draft_post = process_single_news(raw_news, config, draft_only=True)
            if success and isinstance(draft_post, dict):
                # Firestore'a ekle ve Telegram onayı gönder
                db = firebase_helper.init_firebase()
                pending_ref = db.collection("pending_posts").document()
                p_doc_id = pending_ref.id
                
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
                
                success_count += 1
                success_news.append((raw_news.get("title", "Yeni Haber"), "taslak"))
            else:
                failed_news.append((raw_news.get("title", "Bilinmeyen Başlık"), draft_post or "Yazım veya görsel üretim adımı başarısız oldu."))
        except Exception as e:
            err_msg = f"Haber işlenirken beklenmedik hata oluştu: {e}"
            print(err_msg)
            failed_news.append((raw_news.get("title", "Bilinmeyen Başlık"), err_msg))
            
    print(f"\nAkış Tamamlandı. {len(new_news)} haberden {success_count} tanesi taslak olarak kaydedildi ve onaya sunuldu.")
    
    # 7. Sonuçları Kaydet ve Kilidi Kaldır
    # Haber üretimi başarılı olsun veya olmasın tarama yapıldı, last_run_time güncellenmeli
    try:
        rebuild_posts_index_locally()
    except Exception as idx_err:
        print(f"Error rebuilding index on pipeline end: {idx_err}")
    firebase_helper.update_scheduler_config(last_run_time=time.time(), is_running=False)
    
    # 8. Raporlama ve Hata Bildirimi (Telegram)
    report_msg = ""
    if success_news:
        success_details = "\n".join([f"- <b>{t}</b> (Yayın Onayı Bekliyor)" for t, s in success_news])
        report_msg += f"📝 <b>Yayın Onayı Bekleyen Taslaklar ({len(success_news)} adet):</b>\n{success_details}\n\n"
        
    if failed_news:
        failed_details = "\n".join([f"- <b>{t}</b>: {d}" for t, d in failed_news])
        report_msg += f"❌ <b>Başarısız Olan Haberler ({len(failed_news)} adet):</b>\n{failed_details}\n\n"
        
    # Eğer bu çalışmada hata alan API anahtarları varsa rapora ekle
    if ai_writer.FAILED_KEYS_THIS_RUN:
        keys_details = "\n".join([f"- 🔑 <code>{k}</code>: {err[:60]}..." for k, err in ai_writer.FAILED_KEYS_THIS_RUN])
        report_msg += f"⚠️ <b>Hata Alan API Anahtarları (Sondan 6 Hane):</b>\n{keys_details}\n\n"
    
    # Kara liste istatistiklerini ekle
    try:
        blacklist_size = len(firebase_helper.get_blacklisted_links())
        report_msg += f"🛡️ <b>Kara Liste Durumu:</b> Toplam {blacklist_size} engellenmiş link\n\n"
    except Exception:
        pass
        
    if report_msg:
        # En alta canlı site linkini ekle
        report_msg += "🔗 <b>Canlı Haber Sitesi:</b> <a href='https://aihaberler.web.app'>aihaberler.web.app</a>\n"
        
        if failed_news:
            send_error(
                "Haber Portalı Akışı - Rapor", 
                report_msg
            )
        else:
            send_success(
                "Haber Portalı Akışı - Başarılı!", 
                report_msg
            )

    # 9. Normal akış bittikten sonra, otonom araştırmanın vaktinin gelip gelmediğini kontrol et ve çalıştır
    try:
        print("\nOtonom araştırma kontrolü yapılıyor...")
        from autonomous_research import run_autonomous_research
        run_autonomous_research(force=False)
    except Exception as research_err:
        print(f"Otonom araştırma kontrolü sırasında hata: {research_err}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err_msg = f"Sistemde kritik bir hata oluştu: {e}\n{traceback.format_exc()}"
        print(f"KRİTİK HATA: {err_msg}")
        send_error("Haber Portalı Kritik Çalışma Hatası", err_msg)
        # Kritik hata olsa dahi kilidi güvenli kaldır
        try:
            firebase_helper.update_scheduler_config(is_running=False)
        except:
            pass
        sys.exit(1)
