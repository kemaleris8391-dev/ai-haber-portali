import os
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dotenv import load_dotenv

load_dotenv(override=True)

def initialize_firebase():
    if not firebase_admin._apps:
        # GitHub Actions ortamında FIREBASE_SERVICE_ACCOUNT_KEY json metni olarak alınacak.
        # Yerel ortamda dosya yolu olarak.
        cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
        if cred_json:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp:
                temp.write(cred_json)
                temp_path = temp.name
            cred = credentials.Certificate(temp_path)
        else:
            cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "backend-scripts/firebase_credentials.json"))
        firebase_admin.initialize_app(cred)
    return firestore.client()

def export_settings():
    db = initialize_firebase()
    print("Firestore'dan ayarlar çekiliyor...")

    # 1. Site Ayarlarını .env dosyasına yaz
    site_settings_ref = db.collection('system_config').document('site_settings')
    site_settings = site_settings_ref.get().to_dict()

    if site_settings:
        env_path = os.path.join("web-portal", ".env")
        # .env dosyasındaki mevcut anahtarları oku ki üzerine yazarken diğerleri kaybolmasın
        # Ya da sadece .env dosyasına append yapabiliriz ama var olanları değiştirmek en iyisi.
        # Astro için gerekli ortam değişkenlerini oluştur.
        
        env_content = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    if not line.startswith("PUBLIC_BRAND_NAME=") and \
                       not line.startswith("PUBLIC_CONTACT_EMAIL=") and \
                       not line.startswith("PUBLIC_SITE_URL="):
                        env_content.append(line.strip())
        
        env_content.append(f'PUBLIC_BRAND_NAME="{site_settings.get("PUBLIC_BRAND_NAME", "")}"')
        env_content.append(f'PUBLIC_CONTACT_EMAIL="{site_settings.get("PUBLIC_CONTACT_EMAIL", "")}"')
        env_content.append(f'PUBLIC_SITE_URL="{site_settings.get("PUBLIC_SITE_URL", "")}"')

        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(env_content) + "\n")
        print(f"✅ {env_path} güncellendi.")
    else:
        print("❌ Site ayarları bulunamadı!")

    # 2. Gemini Promptlarını JSON dosyasına yaz
    gemini_prompts_ref = db.collection('system_config').document('gemini_prompts')
    gemini_prompts = gemini_prompts_ref.get().to_dict()

    if gemini_prompts:
        json_path = os.path.join("backend-scripts", "prompts_config.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(gemini_prompts, f, ensure_ascii=False, indent=4)
        print(f"✅ {json_path} oluşturuldu.")
    else:
        print("❌ Gemini promptları bulunamadı!")

if __name__ == "__main__":
    export_settings()
