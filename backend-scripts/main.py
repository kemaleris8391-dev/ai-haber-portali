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
            
            # Delete processed deletion_queue document from Firestore
            try:
                doc.reference.delete()
                print(f"Deleted processed queue document: {doc.id}")
            except Exception as e:
                print(f"Error deleting queue document from Firestore: {e}")
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

def cleanup_duplicate_pending_posts():
    print("Running duplicate pending approval drafts cleanup...")
    try:
        import firebase_helper
        from telegram_notifier import edit_message_text
        from fetcher import get_all_published_urls
        
        db = firebase_helper.init_firebase()
        pending_ref = db.collection("pending_posts")
        docs = pending_ref.stream()
        
        local_published_urls = get_all_published_urls()
        
        def is_internal_url(url):
            if not url:
                return True
            url_lower = url.lower()
            return "aihaberler.web.app" in url_lower or "ai-haber-portali.vercel.app" in url_lower or "localhost" in url_lower
            
        all_docs = []
        published_or_queued_urls = set()
        
        for url in local_published_urls:
            if not is_internal_url(url):
                published_or_queued_urls.add(url)
                
        for doc in docs:
            data = doc.to_dict()
            data["_doc_id"] = doc.id
            all_docs.append(data)
            
            status = data.get("status")
            source_url = data.get("sourceUrl")
            
            if status in ["published", "queued_for_publish"] and source_url:
                if not is_internal_url(source_url):
                    published_or_queued_urls.add(source_url)
                    
        deleted_count = 0
        for data in all_docs:
            status = data.get("status")
            source_url = data.get("sourceUrl")
            doc_id = data["_doc_id"]
            
            if status == "pending_approval" and source_url in published_or_queued_urls:
                if not is_internal_url(source_url):
                    print(f"Deleting duplicate pending draft: {doc_id} | Title: {data.get('title')}")
                    # Delete doc from Firestore
                    pending_ref.document(doc_id).delete()
                    
                    # Update Telegram message
                    msg_id = data.get("telegram_message_id")
                    if msg_id:
                        cancel_text = (
                            "⚠️ <b>Bu taslak otomatik olarak iptal edilmiştir.</b>\n\n"
                            f"<b>Başlık:</b> {data.get('title')}\n\n"
                            "Bu haber zaten onaylanıp başka bir başlıkla yayınlandığı için bu mükerrer taslak kaldırılmıştır."
                        )
                        try:
                            edit_message_text(cancel_text, msg_id)
                        except Exception as tg_err:
                            print(f"Error updating telegram message {msg_id}: {tg_err}")
                            
                    deleted_count += 1
                    
        print(f"Duplicate cleanup completed. Total deleted: {deleted_count}")
    except Exception as e:
        print(f"Error in cleanup_duplicate_pending_posts: {e}")

def process_publish_queue():
    # 0. Clean up duplicate pending posts first
    cleanup_duplicate_pending_posts()
    
    print("Checking publish queue for approved drafts...")
    try:
        import firebase_helper
        from ai_writer import enrich_news_with_comment_in_writer
        from telegram_notifier import edit_message_text, send_message
        import json
        import html
        from datetime import datetime, timezone, timedelta
        tr_tz = timezone(timedelta(hours=3))
        
        db = firebase_helper.init_firebase()
        pending_ref = db.collection("pending_posts")
        
        # Query drafts that are queued_for_publish
        queued_drafts = pending_ref.where("status", "==", "queued_for_publish").stream()
        
        published_count = 0
        
        for doc in queued_drafts:
            data = doc.to_dict()
            doc_id = doc.id
            title = data.get("title")
            user_comment = data.get("user_comment", "")
            slug = data.get("slug")
            
            print(f"Processing publish queue item: '{title}' (ID: {doc_id})")
            
            try:
                # 1. Gemma ile başlık ve içeriği zenginleştir
                enriched_data = enrich_news_with_comment_in_writer(data, user_comment)
                if not enriched_data:
                    raise ValueError("Gemma zenginleştirme sonucunda boş veri döndü.")
                    
                new_title = enriched_data["title"]
                new_content = enriched_data["content"]
                
                keywords = data.get("keywords", [])
                category = data.get("category", "pc")
                astro_image_path = data.get("heroImage", "/images/default-news.png")
                source_name = data.get("sourceName", "AI")
                source_url = data.get("sourceUrl", "")
                
                # 2. Markdown içeriğini oluştur
                updated_markdown = f"""---
title: "{new_title}"
description: "{data['description']}"
pubDate: "{datetime.now(tr_tz).strftime('%Y-%m-%dT%H:%M:%S')}"
heroImage: "{astro_image_path}"
category: "{category}"
tags: {json.dumps(keywords, ensure_ascii=False)}
sourceName: "{source_name}"
sourceUrl: "{source_url}"
---
{new_content}
"""
                
                # 3. Markdown dosyasını diskte yerel olarak kaydet (böylece push adımı bunu algılar ve github'a yükler!)
                blog_dir = os.path.abspath(os.path.join(base_dir, "../web-portal/src/content/blog"))
                os.makedirs(blog_dir, exist_ok=True)
                file_path = os.path.join(blog_dir, f"{slug}.md")
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_markdown)
                print(f"Markdown file written locally: {file_path}")
                
                # 3.5. Editör Görüşünü Günlüğe Kaydet (Training Data)
                try:
                    training_file = os.path.abspath(os.path.join(base_dir, "editor_training_data.json"))
                    training_records = []
                    if os.path.exists(training_file):
                        try:
                            with open(training_file, "r", encoding="utf-8") as tf:
                                training_records = json.load(tf)
                        except Exception as read_err:
                            print(f"Error reading existing training file, initializing new one: {read_err}")
                            training_records = []
                    
                    training_records.append({
                        "timestamp": datetime.now(tr_tz).isoformat(),
                        "category": category,
                        "title": title,
                        "summary": data.get("description", ""),
                        "editor_comment": user_comment,
                        "slug": slug,
                        "source_url": source_url
                    })
                    
                    with open(training_file, "w", encoding="utf-8") as tf:
                        json.dump(training_records, tf, ensure_ascii=False, indent=2)
                    print(f"Editor training data logged successfully: {training_file}")
                except Exception as log_err:
                    print(f"Error logging editor training data: {log_err}")
                
                # 4. Firestore taslağı güncelle
                doc.reference.update({
                    "status": "published", 
                    "published_at": time.time(),
                    "title": new_title,
                    "markdown_content": updated_markdown,
                    "content": new_content
                })
                
                # 5. Orijinal Telegram bildirim mesajını güncelle
                telegram_message_id = data.get("telegram_message_id")
                if telegram_message_id:
                    success_text = (
                        "✅ <b>Haber Kişisel Yorumunuzla Birlikte Yayınlandı! (Görüş Kutucuğu İle)</b>\n\n"
                        f"<b>Yeni Başlık:</b> {html.escape(new_title)}\n"
                        f"<b>Kategori:</b> {category.upper()}\n\n"
                        f"<b>Editörün Görüşü:</b> <i>{html.escape(user_comment)}</i>\n\n"
                        "🚀 Makale depoya başarıyla yazıldı. Canlı site 1-2 dakika içinde güncellenecektir."
                    )
                    try:
                        edit_message_text(success_text, telegram_message_id)
                    except Exception as e:
                        print(f"Error editing original telegram message: {e}")
                        
                send_message(f"🎉 <b>{html.escape(new_title)}</b> başlığıyla haber başarıyla yayına alındı!")
                published_count += 1
                
            except Exception as item_err:
                print(f"Error publishing item {doc_id}: {item_err}")
                import traceback
                traceback.print_exc()
                
        print(f"Publish queue processing completed. Total published: {published_count}")
        
        # Eğer herhangi bir haber yayınlandıysa, yerel indeks rebuild edilmeli
        if published_count > 0:
            rebuild_posts_index_locally()
            
    except Exception as e:
        print(f"Error in process_publish_queue: {e}")

def main():
    # 0. Günlük silme kuyruğunu çalıştır
    process_daily_deletions()

    # 0.5. Haber yayınlama kuyruğunu çalıştır
    process_publish_queue()

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
