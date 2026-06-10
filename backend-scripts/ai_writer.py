import os
import re
import json
import io
import time
import requests
from datetime import datetime, timezone, timedelta
TR_TZ = timezone(timedelta(hours=3))
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# .env dosyasını yükle
load_dotenv(override=True)

def slugify(text):
    """Metni SEO dostu URL slug haline getirir."""
    # Türkçe karakter dönüşümleri
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    text = text.translate(tr_map)
    text = text.lower()
    # Sadece İngilizce ASCII harf, sayı, boşluk ve tirelere izin ver
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    # Windows MAX_PATH (dosya yolu sınırı) koruması için 60 karakterle kısıtla
    text = text[:60]
    # Kırpma sonrası sonda kalan tireleri temizle
    text = re.sub(r"-+$", "", text)
    return text

# .env dosyasından gelen çoklu API anahtarlarını yükle
API_KEYS = []
keys_str = os.getenv("GEMINI_API_KEYS")
if keys_str:
    API_KEYS = [k.strip() for k in keys_str.split(",") if k.strip()]

current_key_idx = 0
FAILED_KEYS_THIS_RUN = [] # Her çalışmada başarısız olan (masked_key, error_msg) ikililerini tutar
DOWNLOADED_PHOTO_IDS = set() # Aynı çalışmada mükerrer görsel indirilmesini engellemek için

# .env dosyasından gelen çoklu Pexels API anahtarlarını yükle
PEXELS_API_KEYS = []
pexels_keys_str = os.getenv("PEXELS_API_KEY")
if pexels_keys_str:
    PEXELS_API_KEYS = [k.strip() for k in pexels_keys_str.split(",") if k.strip()]

current_pexels_key_idx = 0

PROMPTS_CONFIG = {}
_prompts_file = os.path.join(os.path.dirname(__file__), "prompts_config.json")
if os.path.exists(_prompts_file):
    with open(_prompts_file, "r", encoding="utf-8") as f:
        PROMPTS_CONFIG = json.load(f)

def rotate_pexels_key():
    global current_pexels_key_idx
    if PEXELS_API_KEYS:
        current_pexels_key_idx = (current_pexels_key_idx + 1) % len(PEXELS_API_KEYS)
        print(f"UYARI: Pexels API anahtarı bir sonraki ile değiştiriliyor. (Yeni Sıra: {current_pexels_key_idx + 1}/{len(PEXELS_API_KEYS)})")


def mask_key(key):
    """API anahtarının sondan 6 karakteri hariç diğer kısımlarını maskeler."""
    if not key:
        return "Bilinmeyen Key"
    key_str = str(key).strip()
    if len(key_str) <= 6:
        return key_str
    return f"...{key_str[-6:]}"

def get_next_client():
    global current_key_idx
    if not API_KEYS:
        # Fallback: Klasik GEMINI_API_KEY dene
        fallback_key = os.getenv("GEMINI_API_KEY")
        if fallback_key:
            return genai.Client(api_key=fallback_key.strip())
        print("UYARI: GEMINI_API_KEYS veya GEMINI_API_KEY bulunamadı!")
        return genai.Client()
        
    api_key = API_KEYS[current_key_idx]
    print(f"Bilgi: API Anahtarı {current_key_idx + 1}/{len(API_KEYS)} kullanılıyor. (Baslangic: {api_key[:10]}...)")
    return genai.Client(api_key=api_key)

def rotate_key():
    global current_key_idx
    if API_KEYS:
        current_key_idx = (current_key_idx + 1) % len(API_KEYS)
        print(f"UYARI: API anahtarı bir sonraki ile değiştiriliyor. (Yeni Sıra: {current_key_idx + 1}/{len(API_KEYS)})")

def rewrite_news_with_ai(raw_title, raw_summary, category, raw_link, source_name, model_name="gemma-4-31b-it"):
    """Gemini API kullanarak haberi özgünleştirir. Hata (429/403/500) durumunda model fallback ve anahtar rotasyonu yapar."""
    prompt = PROMPTS_CONFIG.get("rewrite_prompt", "")
    if not prompt:
        raise ValueError("prompts_config.json içinden rewrite_prompt okunamadı!")
    prompt = prompt.replace("{raw_title}", raw_title).replace("{raw_summary}", raw_summary).replace("{category}", category).replace("{raw_link}", raw_link).replace("{source_name}", source_name)
    max_retries = len(API_KEYS) if API_KEYS else 3
    last_error = "Bilinmeyen API Hatası"
    
    # gemma-4-31b-it birincil olmak üzere, hata durumunda denenecek fallback modelleri
    models_to_try = [model_name, "gemma-4-26b-a4b-it", "gemma-4-26b-it"]
    
    for attempt in range(max_retries):
        client = get_next_client()
        
        for current_model in models_to_try:
            try:
                print(f"Haber özgünleştirme deneniyor: Model={current_model}")
                
                # Önce thinking_config ile en kaliteli sonucu almaya çalış
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(
                                thinking_level="HIGH"
                            )
                        )
                    )
                except Exception as thinking_err:
                    # Eğer model veya API sürümü thinking_config desteklemiyorsa normal modda dene
                    print(f"Model {current_model} thinking_config hatası ({thinking_err}). Normal modda deneniyor...")
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    
                if not response.text:
                    raise ValueError("Model bos yanit dondu. Güvenlik filtresi (Safety Block) tetiklenmis olabilir.")
                data = json.loads(response.text)
                return data
            except Exception as e:
                last_error = str(e)
                print(f"Model {current_model} hatası: {last_error}")
                # Hata durumunda bir sonraki model seçeneğini dene
                continue
                
        # Eğer bu anahtarda hiçbir model çalışmadıysa anahtar rotasyonu yap
        print(f"Hata (Anahtar Denemesi {attempt + 1}/{max_retries}): {last_error}")
        failed_key = API_KEYS[current_key_idx] if API_KEYS else "GEMINI_API_KEY"
        masked = mask_key(failed_key)
        if (masked, last_error) not in FAILED_KEYS_THIS_RUN:
            FAILED_KEYS_THIS_RUN.append((masked, last_error))
        
        is_permanent = "API key not valid" in last_error or "NOT_FOUND" in last_error or "400" in last_error or "403" in last_error
        rotate_key()
        
        if attempt < max_retries - 1:
            if not is_permanent and "429" in last_error:
                wait_time = (attempt + 1) * 2
                print(f"Gecici Hız Limiti (429) algilandi. {wait_time} saniye bekleniyor...")
                time.sleep(wait_time)
            else:
                print("Sonraki anahtarla deneniyor...")
                
    raise Exception(f"Gemini AI Yazim Hatası: {last_error}")

def check_news_semantic_duplicates(candidates, existing_titles, model_name="gemma-4-31b-it"):
    """
    Gemma kullanarak aday haberlerin hem yayın politikasına uygunluğunu (kural)
    hem de mevcut haberlerle ve kendi aralarında mükerrer (kopya) olup olmadığını kontrol eder.
    Adaylar bir sözlük listesidir: [{'id': 1, 'title': '...', 'summary': '...', 'category': '...'}, ...]
    Geriye elenen (mükerrer veya politika dışı olan) adayların ID listesini döner.
    """
    if not candidates:
        return []
        
    recent_existing = existing_titles or []
    
    prompt = PROMPTS_CONFIG.get("semantic_duplicates_prompt", "")
    if not prompt:
        raise ValueError("prompts_config.json içinden semantic_duplicates_prompt okunamadı!")
    
    existing_titles_str = json.dumps(recent_existing, ensure_ascii=False, indent=2)
    candidates_str = json.dumps([{"id": c["id"], "title": c["title"], "category": c.get("category"), "summary": c.get("summary")} for c in candidates], ensure_ascii=False, indent=2)
    
    # Fetch unwanted posts references from Firestore
    unwanted_str = "Henüz istenmeyen/engellenmiş haber kaydı bulunmuyor."
    try:
        import firebase_helper
        db = firebase_helper.init_firebase()
        unwanted_ref = db.collection("unwanted_posts")
        # Get last 20 unwanted posts
        unwanted_docs = unwanted_ref.order_by("added_at", direction="DESCENDING").limit(20).get()
        if unwanted_docs:
            unwanted_list = []
            for doc in unwanted_docs:
                d = doc.to_dict()
                unwanted_list.append({
                    "title": d.get("title", "Başlıksız"),
                    "category": d.get("category", "Bilinmeyen"),
                    "summary": d.get("description", "Özet yok")
                })
            unwanted_str = json.dumps(unwanted_list, ensure_ascii=False, indent=2)
    except Exception as fs_err:
        print(f"Firestore'dan istenmeyen haberler çekilirken hata oluştu: {fs_err}")
        
    prompt = prompt.replace("{existing_titles}", existing_titles_str).replace("{candidates}", candidates_str).replace("{unwanted_posts}", unwanted_str)
    
    max_retries = len(API_KEYS) if API_KEYS else 3
    last_error = "Bilinmeyen API Hatası"
    
    # gemma-4-31b-it birincil olmak üzere, hata durumunda denenecek fallback modelleri
    models_to_try = [model_name, "gemma-4-26b-a4b-it", "gemma-4-26b-it"]
    
    for attempt in range(max_retries):
        client = get_next_client()
        
        for current_model in models_to_try:
            try:
                print(f"Gemma ile yayın öncesi kural ve mükerrerlik analizi yapılıyor: Model={current_model} (Deneme {attempt + 1}/{max_retries})...")
                
                # Önce thinking_config ile en kaliteli sonucu almaya çalış
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(
                                thinking_level="HIGH"
                            )
                        )
                    )
                except Exception as thinking_err:
                    # Eğer model veya API sürümü thinking_config desteklemiyorsa normal modda dene
                    print(f"Model {current_model} thinking_config hatası ({thinking_err}). Normal modda deneniyor...")
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                
                if not response.text:
                    raise ValueError("Model boş yanıt döndü.")
                    
                data = json.loads(response.text)
                results = data.get("results", [])
                
                rejected_ids = []
                for res in results:
                    c_id = res.get("id")
                    is_compliant = res.get("is_compliant", True)
                    is_duplicate = res.get("is_duplicate", False)
                    reason = res.get("reason", "Açıklama belirtilmedi.")
                    
                    # Başlığı loglamak için adaylardan bulalım
                    title_str = "Bilinmeyen Başlık"
                    try:
                        title_str = next(c['title'] for c in candidates if c['id'] == c_id)
                    except StopIteration:
                        pass
                    
                    if not is_compliant:
                        rejected_ids.append(c_id)
                        print(f"🛡️ AI Filtresi (Politika Dışı) Elendi: '{title_str}' -> Gerekçe: {reason}")
                    elif is_duplicate:
                        rejected_ids.append(c_id)
                        print(f"🔍 AI Filtresi (Mükerrer/Kopya) Elendi: '{title_str}' -> Gerekçe: {reason}")
                    else:
                        print(f"✅ AI Filtresi (Onaylandı): '{title_str}' -> Gerekçe: {reason}")
                               
                return rejected_ids
                
            except Exception as e:
                last_error = str(e)
                print(f"Model {current_model} semantik değerlendirme hatası: {last_error}")
                continue
                
        # Eğer bu anahtarda hiçbir model çalışmadıysa anahtar rotasyonu yap
        print(f"AI Semantik Değerlendirme Hatası (Deneme {attempt + 1}/{max_retries}): {last_error}")
        failed_key = API_KEYS[current_key_idx] if API_KEYS else "GEMINI_API_KEY"
        masked = mask_key(failed_key)
        if (masked, last_error) not in FAILED_KEYS_THIS_RUN:
            FAILED_KEYS_THIS_RUN.append((masked, last_error))
            
        is_permanent = "API key not valid" in last_error or "NOT_FOUND" in last_error or "400" in last_error or "403" in last_error
        rotate_key()
        
        if attempt < max_retries - 1:
            if not is_permanent and "429" in last_error:
                wait_time = (attempt + 1) * 2
                print(f"Hız limiti beklemesi: {wait_time} sn...")
                time.sleep(wait_time)
            else:
                print("Sonraki anahtarla deneniyor...")
            
    print(f"KRİTİK UYARI: Toplu semantik doğrulama tamamen başarısız oldu. Geri çekilme: Tüm adaylar onaylanıyor. Detay: {last_error}")
    return []



def generate_image_with_imagen(image_prompt, output_path, model_name="imagen-3.0-generate-002"):
    """Imagen API kullanarak haber için 16:9 görsel üretir ve kaydeder."""
    max_retries = len(API_KEYS) if API_KEYS else 3
    last_error = "Görsel üretilemedi"
    for attempt in range(max_retries):
        client = get_next_client()
        try:
            print(f"Imagen ile görsel üretiliyor. Prompt: {image_prompt}")
            result = client.models.generate_images(
                model=model_name,
                prompt=image_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    output_mime_type="image/jpeg"
                )
            )
            
            if not result.generated_images:
                raise ValueError("Imagen bos görsel kümesi döndürdü.")
                
            for generated_image in result.generated_images:
                image_bytes = generated_image.image.image_bytes
                image = Image.open(io.BytesIO(image_bytes))
                
                # Klasör yoksa oluştur
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                image.save(output_path, "JPEG")
                print(f"Görsel başarıyla kaydedildi: {output_path}")
                return True
        except Exception as e:
            last_error = str(e)
            print(f"Hata (Imagen - Deneme {attempt + 1}/{max_retries}): {last_error}")
            
            # Imagen modeli ücretsiz planda desteklenmiyorsa veya API anahtarı geçersizse boşuna 8 kere deneme, direkt Fast Fail yap!
            is_unsupported = "not found" in last_error.lower() or "not supported" in last_error.lower() or "404" in last_error
            is_permanent = "API key not valid" in last_error or "400" in last_error or "403" in last_error or is_unsupported
            
            rotate_key()
            
            if is_unsupported:
                print("BİLGİ: Imagen modeli bu API anahtarlarıyla desteklenmiyor (Ücretsiz Sürüm). Hızlıca Pexels Fallback adımına geçiliyor...")
                break
                
            if attempt < max_retries - 1:
                if not is_permanent and "429" in last_error:
                    wait_time = (attempt + 1) * 2
                    print(f"Gecici Hız Limiti (429) algilandi. {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                else:
                    print("Beklemeden sonraki anahtar deneniyor...")
                
    raise Exception(f"Imagen Görsel Hatası: {last_error}")

def fetch_pexels_image(query, output_path):
    """Pexels API üzerinden telifsiz görsel arar ve kaydeder."""
    global current_pexels_key_idx
    if not PEXELS_API_KEYS:
        print("UYARI: PEXELS_API_KEY bulunamadı!")
        return False
        
    max_attempts = len(PEXELS_API_KEYS)
    for attempt in range(max_attempts):
        api_key = PEXELS_API_KEYS[current_pexels_key_idx]
        print(f"Pexels üzerinden görsel aranıyor (Anahtar {current_pexels_key_idx + 1}/{len(PEXELS_API_KEYS)}): '{query}'")
        headers = {"Authorization": api_key.strip()}
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    # Aynı çalışma zamanı içinde mükerrer görsel indirilmesini engelle
                    selected_photo = None
                    for photo in data["photos"]:
                        photo_id = photo.get("id")
                        if photo_id not in DOWNLOADED_PHOTO_IDS:
                            selected_photo = photo
                            DOWNLOADED_PHOTO_IDS.add(photo_id)
                            break
                    
                    # Eğer hepsi daha önce indirildiyse ilk görseli fallback olarak kullan
                    if not selected_photo:
                        selected_photo = data["photos"][0]
                        
                    photo_url = selected_photo["src"]["large2x"]
                    img_response = requests.get(photo_url, timeout=10)
                    if img_response.status_code == 200:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(img_response.content)
                        print(f"Pexels görseli başarıyla indirildi: {output_path} (ID: {selected_photo.get('id')})")
                        return True
            
            print(f"Hata: Pexels API isteği başarısız oldu. Durum Kodu: {response.status_code} (Anahtar: {mask_key(api_key)})")
            if attempt < max_attempts - 1:
                rotate_pexels_key()
        except Exception as e:
            print(f"Hata: Pexels görseli çekilemedi. Detay: {e}")
            if attempt < max_attempts - 1:
                rotate_pexels_key()
                
    return False

def convert_to_optimized_webp(input_path, output_path, max_width=1200, quality=82):
    """
    Herhangi bir formattaki görseli (JPG, PNG, WebP, GIF vb.) optimize edilmiş WebP formatına dönüştürür.
    - Google Keşfet minimum genişlik şartı: 1200px (bunu korur, küçük görselleri büyütmez).
    - Kalite: 82 (gözle fark edilemez kayıp, dosya boyutu ~%60-70 küçülür).
    - EXIF ve ICC profil verilerini temizleyerek dosya boyutunu daha da düşürür.
    """
    try:
        img = Image.open(input_path)
        
        # Şeffaf (RGBA/P) görselleri RGB'ye çevir (WebP lossy için gerekli)
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (18, 18, 18))  # Sitenin koyu arka plan rengi
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # Genişlik 1200px'den büyükse orantılı küçült (Google Keşfet için 1200px yeterli)
        w, h = img.size
        if w > max_width:
            ratio = max_width / w
            new_h = int(h * ratio)
            img = img.resize((max_width, new_h), Image.LANCZOS)
            print(f"  Görsel boyutlandırıldı: {w}x{h} → {max_width}x{new_h}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, "WEBP", quality=quality, method=4)
        
        # Boyut karşılaştırması logla
        original_size = os.path.getsize(input_path) / 1024  # KB
        webp_size = os.path.getsize(output_path) / 1024  # KB
        savings = ((original_size - webp_size) / original_size * 100) if original_size > 0 else 0
        print(f"  WebP Optimizasyonu: {original_size:.0f}KB → {webp_size:.0f}KB (-%{savings:.0f} tasarruf)")
        return True
    except Exception as e:
        print(f"  WebP dönüşüm hatası: {e}")
        return False

def save_news_as_markdown(news_data, output_dir, images_dir, source_name, source_url, og_image=None, draft_only=False):
    """Haber verilerini Astro blog uyumlu Markdown olarak kaydeder veya taslak olarak döner."""
    title = news_data["title"].replace('"', "'")
    content = news_data["content"]
    description = news_data["description"].replace('"', "'")
    keywords = news_data["keywords"]
    category = news_data.get("category", "pc").strip().lower()
    
    # Kategori Sınırlama Koruyucusu (Category Safeguard)
    # Telegram/Bot taleplerinde veya AI halüsinasyonlarında izin verilmeyen kategoriler engellenir
    ALLOWED_CATEGORIES = {"plc", "pc", "endustriyel-makinalar", "oyun", "yapay-zeka", "akilli-ev"}
    if category not in ALLOWED_CATEGORIES:
        if "plc" in category or "otomasyon" in category or "automation" in category:
            category = "plc"
        elif "tamir" in category or "bakim" in category or "repair" in category or "maintenance" in category or "makina" in category or "machinery" in category:
            category = "endustriyel-makinalar"
        elif "oyun" in category or "game" in category or "gaming" in category:
            category = "oyun"
        elif "yapay" in category or "ai" in category or "intelligence" in category:
            category = "yapay-zeka"
        elif "ev" in category or "akıllı" in category or "smart" in category or "iot" in category or "süpürge" in category or "vacuum" in category:
            category = "akilli-ev"
        else:
            category = "pc"
    
    slug = slugify(title)
    date_str = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    
    # Görsel adı ve yolları (WebP formatı)
    image_filename = f"{slug}.webp"
    temp_download_path = os.path.join(images_dir, f"{slug}_temp_raw")  # Geçici indirme dosyası
    image_local_path = os.path.join(images_dir, image_filename)
    # Astro public klasörüne göre görsel yolu (örn: /images/news/slug.webp)
    astro_image_path = f"/images/news/{image_filename}"
    
    # Doğrudan Pexels Telifsiz Görsel Arama
    pexels_query = news_data.get("pexels_query", category)
    success = False

    # 1. Aşama: Orijinal Haber Görseli (og:image) Denemesi
    if og_image:
        try:
            print(f"Orijinal görsel indiriliyor: {og_image}")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            res = requests.get(og_image, headers=headers, timeout=10)
            if res.status_code == 200:
                os.makedirs(os.path.dirname(temp_download_path), exist_ok=True)
                with open(temp_download_path, "wb") as f:
                    f.write(res.content)
                # WebP'ye dönüştür ve optimize et
                if convert_to_optimized_webp(temp_download_path, image_local_path):
                    success = True
                    print(f"Orijinal görsel başarıyla WebP'ye dönüştürüldü.")
                else:
                    print(f"Orijinal görsel WebP dönüşümü başarısız. Pexels fallback...")
                # Geçici dosyayı temizle
                if os.path.exists(temp_download_path):
                    os.remove(temp_download_path)
            else:
                print(f"Orijinal görsel HTTP {res.status_code} hatası verdi.")
        except Exception as e:
            print(f"og:image indirme hatası: {e}. Pexels fallback uygulanıyor...")
            if os.path.exists(temp_download_path):
                os.remove(temp_download_path)

    # 2. Aşama: Pexels Fallback
    if not success:
        try:
            # Pexels görseli de önce geçici dosyaya indirilir, sonra WebP'ye dönüştürülür
            pexels_downloaded = fetch_pexels_image(pexels_query, temp_download_path)
            if pexels_downloaded:
                if convert_to_optimized_webp(temp_download_path, image_local_path):
                    success = True
                else:
                    # WebP dönüşümü başarısız olursa ham dosyayı doğrudan kullan
                    import shutil
                    shutil.move(temp_download_path, image_local_path)
                    success = True
                # Geçici dosyayı temizle
                if os.path.exists(temp_download_path):
                    os.remove(temp_download_path)
        except Exception as e:
            print(f"Pexels görseli cekilemedi: {e}")
            if os.path.exists(temp_download_path):
                os.remove(temp_download_path)
        
    if not success:
        # Pexels de başarısız olursa default-news.png ata
        print("Pexels görseli çekilemedi. Fallback default-news.png ataniyor.")
        astro_image_path = "/images/default-news.png"
    
    # Markdown İçeriği
    markdown_content = f"""---
title: "{title}"
description: "{description}"
pubDate: "{datetime.now(TR_TZ).strftime('%Y-%m-%dT%H:%M:%S')}"
heroImage: "{astro_image_path}"
category: "{category}"
tags: {json.dumps(keywords, ensure_ascii=False)}
sourceName: "{source_name}"
sourceUrl: "{source_url}"
---
{content}
"""
    
    if draft_only:
        print(f"Haber taslak olarak üretildi (Markdown dosyası oluşturulmadı): {slug}")
        return {
            "title": title,
            "content": content,
            "description": description,
            "category": category,
            "keywords": keywords,
            "heroImage": astro_image_path,
            "slug": slug,
            "sourceName": source_name,
            "sourceUrl": source_url,
            "markdown_content": markdown_content
        }

    # Markdown dosyasını kaydet
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{slug}.md")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"Haber Markdown dosyası oluşturuldu: {file_path}")
    return file_path

def process_single_news(raw_news, config, draft_only=False):
    """Tek bir haberi Gemini ile işler, görselini üretir ve kaydeder veya taslak olarak döner."""
    print(f"\nİşleniyor: {raw_news['title']}")
    
    try:
        # 1. AI ile yeniden yaz
        ai_data = rewrite_news_with_ai(
            raw_news["title"], 
            raw_news["summary"], 
            raw_news["category"],
            raw_news["link"],
            raw_news["source"],
            model_name=config["gemini"]["model"]
        )
        
        if not ai_data:
            return False, "Model bos veya gecersiz JSON döndürdü."
            
        if "error" in ai_data:
            return False, f"Haber kapsam dışı olduğu için elendi: {ai_data['error']}"
            
        # Kategori bilgisini ekle
        ai_data["category"] = raw_news["category"]
        
        # Regex Temizliği: AI halüsinasyonlarını temizle ("Link burada", "haberin detayı için tıklayın" vb.)
        content = ai_data.get("content", "")
        # "[Link burada](...)" veya benzeri kalıpları ve cümleleri yakala
        content = re.sub(r'(?i)(buradan\s+ulaşabilirsiniz|link\s+burada|haberin\s+tamamı|detaylar\s+için\s+tıklayın|orijinal\s+habere\s+gitmek\s+için).*?(?=\n|$)', '', content)
        content = re.sub(r'\[(?:Link burada|Tıklayın|Orijinal Haber)\]\([^)]+\)', '', content)
        ai_data["content"] = content.strip()
        
        # Klasör yollarını al
        output_dir = config["settings"]["output_dir"]
        images_dir = config["settings"]["images_dir"]
        
        # Göreceli yolları tam yola çevir (backend-scripts klasörüne göre)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_output_dir = os.path.abspath(os.path.join(base_dir, output_dir))
        abs_images_dir = os.path.abspath(os.path.join(base_dir, images_dir))
        
        # 2. Markdown ve Görsel olarak kaydeder
        result = save_news_as_markdown(
            ai_data, 
            abs_output_dir, 
            abs_images_dir, 
            raw_news["source"], 
            raw_news["link"],
            raw_news.get("og_image"),
            draft_only=draft_only
        )
        
        if draft_only:
            return True, result
            
        return True, slugify(ai_data["title"])
    except Exception as e:
        return False, str(e)

def research_topic_with_gemini(user_prompt):
    """Gemini 2.5 Flash ve Google Search Grounding kullanarak konuyu araştırıp haber yazar."""
    stripped_prompt = user_prompt.strip()
    is_single_url = not " " in stripped_prompt and (stripped_prompt.startswith("http://") or stripped_prompt.startswith("https://"))
    
    # Detaylı araştırma tespiti: Uzunluğu 200'den büyükse ve sadece tek bir URL değilse
    is_detailed_research = len(stripped_prompt) > 200 and not is_single_url
    
    if is_detailed_research:
        prompt = PROMPTS_CONFIG.get("detailed_research_prompt", "")
        if not prompt:
            raise ValueError("prompts_config.json içinden detailed_research_prompt okunamadı!")
        prompt = prompt.replace("{user_prompt}", user_prompt)
    else:
        prompt = PROMPTS_CONFIG.get("search_research_prompt", "")
        if not prompt:
            raise ValueError("prompts_config.json içinden search_research_prompt okunamadı!")
        prompt = prompt.replace("{user_prompt}", user_prompt)

    max_retries = len(API_KEYS) if API_KEYS else 3
    for attempt in range(max_retries):
        client = get_next_client()
        try:
            if is_detailed_research:
                print(f"Gemini ile konu yazılıyor (Detaylı araştırma metni algılandı, Google Search devre dışı)...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
            else:
                print(f"Gemini ile konu araştırılıyor (Google Search Grounding aktif)...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}]
                    )
                )
            
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(text.strip())
            return data
        except Exception as e:
            err_msg = str(e)
            print(f"Hata (Gemini Araştırma - Deneme {attempt + 1}/{max_retries}): {err_msg}")
            
            # Başarısız olan API anahtarını maskeleyip listeye ekle
            failed_key = API_KEYS[current_key_idx] if API_KEYS else "GEMINI_API_KEY"
            masked = mask_key(failed_key)
            if (masked, err_msg) not in FAILED_KEYS_THIS_RUN:
                FAILED_KEYS_THIS_RUN.append((masked, err_msg))
                
            rotate_key()
    return None

def enrich_news_with_comment_in_writer(draft_data, user_comment, model_name="gemma-4-31b-it"):
    """
    Gemma kullanarak editoryal görüşü haber metnine zenginleştirici olarak ekler.
    """
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

    max_retries = len(API_KEYS) if API_KEYS else 3
    last_error = "Bilinmeyen API Hatası"
    models_to_try = [model_name, "gemma-4-26b-a4b-it", "gemma-4-26b-it", "gemini-2.5-flash"]
    
    for attempt in range(max_retries):
        client = get_next_client()
        
        for current_model in models_to_try:
            try:
                print(f"Gemma ile yorum zenginleştirme deneniyor: Model={current_model} (Deneme {attempt + 1}/{max_retries})...")
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(
                                thinking_level="HIGH"
                            )
                        )
                    )
                except Exception as thinking_err:
                    print(f"Model {current_model} thinking_config hatası. Normal modda deneniyor...")
                    response = client.models.generate_content(
                        model=current_model,
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
            except Exception as e:
                last_error = str(e)
                print(f"Model {current_model} zenginleştirme hatası: {last_error}")
                continue
                
        rotate_key()
        
    raise Exception(f"Gemma Zenginleştirme Hatası: {last_error}")

