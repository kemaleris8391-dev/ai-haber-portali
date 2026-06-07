import os
import requests
from dotenv import load_dotenv

# Load env variables
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(workspace_root, "backend-scripts", ".env")
load_dotenv(env_path, override=True)

api_keys_str = os.getenv("PEXELS_API_KEY")
if not api_keys_str:
    print("HATA: PEXELS_API_KEY bulunamadı!")
    exit(1)

PEXELS_API_KEYS = [k.strip() for k in api_keys_str.split(",") if k.strip()]
current_pexels_key_idx = 0

images_dir = os.path.join(workspace_root, "web-portal", "public", "images", "news")

# Global set to avoid duplicates during this run
USED_PHOTO_IDS = set()

# Map duplicate filenames to specific queries
duplicate_queries = {
    # Group 1
    "akilli-telefon-dunyasinda-haziran-2026-rehberi-her-butceye-u.jpg": "smartphone review table",
    "samsungdan-genisleme-hamlesi-one-ui-85-bes-yeni-modele-daha.jpg": "samsung galaxy mobile screen",
    # Group 2
    "amazon-prime-gaming-haziran-2026-kutuphanesini-guncelledi-is.jpg": "amazon prime gaming gamepad",
    "yerli-studyo-umuro-gameden-nintendo-switche-yepyeni-bir-macera-akita-legends-squad-cikti.jpg": "nintendo switch gamepad console",
    # Group 3
    "control-resonant-pc-sistem-gereksinimleri-aciklandi-donaniml.jpg": "pc specs system hardware",
    "msidan-oyun-dunyasinda-devrim-dunyanin-ilk-uc-modlu-qd-oled.jpg": "curved monitor gaming display",
    # Group 4
    "control-resonantta-platform-ayrimciligi-tartismasi-ps5-ozel.jpg": "playstation console disc",
    "playstationin-haziran-2026-favorileri-belli-oldu-sony-en-cok.jpg": "sony dualsense controller",
    # Group 5
    "endustriyel-hesaplamalarda-kuantum-sicramasi-qunova-ve-jhpc.jpg": "industrial supercomputer server rack",
    "quix-quantumdan-onemli-hamle-evrensel-fotonik-kuantum-bilgis.jpg": "photonics optical quantum chip",
    # Group 6 (Fable)
    "fable-ertelemesi-resmen-dogrulandi-efsanevi-rpg-icin-2027-he.jpg": "fable fantasy castle medieval",
    "fable-hayranlarini-uzecek-haber-efsanevi-rpgnin-cikisi-2027y.jpg": "fantasy warrior sword fight",
    "fable-icin-yeni-bir-bekleyis-basladi-gelistirici-ekip-oyunu.jpg": "rpg gamer playing computer",
    "fable-remakein-cikis-tarihi-resmi-olarak-gelecek-yila-ertele.jpg": "dragon fantasy landscape sky",
    "fablein-buyulu-dunyasina-giris-2027ye-uzadi-resmi-aciklama-g.jpg": "mystical forest elf path",
    "fablein-fantastik-dunyasina-yolculuk-uzuyor-cikis-tarihi-202.jpg": "magic sword shield fantasy",
    # Group 7
    "god-of-war-ve-degisen-perspektifler-playstation-serileri-ici.jpg": "viking shield god of war axe",
    "steamos-yeni-nesil-tasinabilir-oyun-cihazlarina-kapi-araliyo.jpg": "steam deck handheld gaming console",
    # Group 8
    "honor-win-turbo-sahneye-cikti-dev-batarya-ve-sinir-tanimaz-d.jpg": "honor phone tech",
    "iphone-18-prodan-ilk-batarya-sizintilari-sim-kart-tercihi-pi.jpg": "iphone battery processor",
    # Group 9
    "james-gunndan-surpriz-paylasim-superman-man-of-tomorrowda-zi.jpg": "superhero cape comic",
    "superman-evreninde-heyecan-artiyor-nicholas-houltun-lex-luth.jpg": "lex luthor villain corporate",
    # Group 10 (Z Fold 8)
    "katlanabilir-iphone-ultra-yolda-tasarim-detaylari-ve-karsila.jpg": "foldable screen phone apple concept",
    "samsung-galaxy-z-fold-8-sahneye-cikiyor-ilk-canli-goruntuler.jpg": "samsung fold phone display screen",
    "samsung-galaxy-z-fold8-ilk-kez-goruntelendi-katlanabilir-ekr.jpg": "foldable mobile device hand",
    "samsungun-yeni-hamlesi-galaxy-z-fold-8-wide-beklentileri-yuk.jpg": "flexible display smartphone tech",
    # Group 11
    "kuantum-bilgisayarlarin-gelecegi-sekilleniyor-yaqumo-nkt-ve.jpg": "quantum circuit processor design",
    "kuantum-devrimi-kapida-birlesik-kralliktaki-dev-sirketler-mi.jpg": "london financial district tech city",
    # Group 12
    "metin2-turkiyede-ikinci-sans-donemi-yasaklanan-hesaplar-icin.jpg": "retro mmorpg gamer desktop pc",
    "steamde-buyuk-firsat-780-tl-degerindeki-oyun-kisa-sureligine.jpg": "steam game library store",
    # Group 13
    "msi-computex-2026ya-damga-vurdu-dort-farkli-urunle-en-iyi-se.jpg": "computex hardware expo exhibition",
    "nvidia-rtx-spark-ilk-testlerde-gorundu-apple-m5-serisi-ile-p.jpg": "nvidia rtx graphics card board",
    # Group 14
    "xiaomi-18-pro-sizintilari-arka-ekran-daha-buyuk-ve-daha-yete.jpg": "xiaomi smartphone back camera lens",
    "xiaomi-hyperos-4-guncellemesi-hangi-cihazlara-geliyor-iste-b.jpg": "xiaomi hyperos settings screen"
}

def rotate_key():
    global current_pexels_key_idx
    current_pexels_key_idx = (current_pexels_key_idx + 1) % len(PEXELS_API_KEYS)
    print(f"UYARI: Pexels API anahtarı sonraki ile değiştiriliyor. (Yeni Sıra: {current_pexels_key_idx + 1}/{len(PEXELS_API_KEYS)})")

def fetch_and_save(filename, query):
    global current_pexels_key_idx
    output_path = os.path.join(images_dir, filename)
    max_attempts = len(PEXELS_API_KEYS)
    
    for attempt in range(max_attempts):
        api_key = PEXELS_API_KEYS[current_pexels_key_idx]
        headers = {"Authorization": api_key.strip()}
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=15&orientation=landscape"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    selected_photo = None
                    for photo in data["photos"]:
                        photo_id = photo.get("id")
                        if photo_id not in USED_PHOTO_IDS:
                            selected_photo = photo
                            USED_PHOTO_IDS.add(photo_id)
                            break
                    
                    if not selected_photo:
                        selected_photo = data["photos"][0]
                        
                    photo_url = selected_photo["src"]["large2x"]
                    img_response = requests.get(photo_url, timeout=10)
                    if img_response.status_code == 200:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(img_response.content)
                        print(f"BAŞARI: '{filename}' için görsel indirildi (Sorgu: '{query}', Pexels ID: {selected_photo.get('id')})")
                        return True
            print(f"Hata: API başarısız. Durum Kodu: {response.status_code} | Dosya: {filename}")
            if attempt < max_attempts - 1:
                rotate_key()
        except Exception as e:
            print(f"Hata: Görsel çekilemedi '{filename}'. Detay: {e}")
            if attempt < max_attempts - 1:
                rotate_key()
    return False

total_fixed = 0
for filename, query in duplicate_queries.items():
    if fetch_and_save(filename, query):
        total_fixed += 1

print(f"\nİşlem Tamamlandı. Toplam {total_fixed} adet mükerrer görsel başarıyla güncellendi.")
