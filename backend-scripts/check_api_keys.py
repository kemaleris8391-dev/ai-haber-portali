# -*- coding: utf-8 -*-
import os
import sys
from dotenv import load_dotenv
from google import genai

# Emojilerin Windows terminalde düzgün yazdırılabilmesi için
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Çalışma dizinini ayarla
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"), override=True)

def mask_key(key):
    """API anahtarının sadece son 6 hanesini görünür kılar."""
    if not key:
        return "Bilinmeyen Key"
    key_str = str(key).strip()
    if len(key_str) <= 6:
        return key_str
    return f"...{key_str[-6:]}"

def ping_api_keys():
    """Tüm API anahtarlarının durumunu test eder ve raporlar."""
    keys_str = os.getenv("GEMINI_API_KEYS")
    if not keys_str:
        print("❌ HATA: .env dosyasında GEMINI_API_KEYS tanımlanmamış!")
        return
        
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    print("==================================================")
    print(f"🔑 GEMINI API ANAHTARI SAĞLIK KONTROLÜ ({len(keys)} Adet)")
    print("==================================================")
    
    valid_count = 0
    invalid_count = 0
    overloaded_count = 0
    
    for idx, key in enumerate(keys, start=1):
        masked = mask_key(key)
        try:
            # Gemini client başlat ve test sorusu sor
            client = genai.Client(api_key=key)
            client.models.generate_content(
                model="gemini-2.5-flash",
                contents="ping"
            )
            print(f"🟢 [Anahtar {idx}] {masked} -> CANLI / AKTİF")
            valid_count += 1
        except Exception as e:
            err = str(e)
            if "API key not valid" in err or "INVALID_ARGUMENT" in err:
                print(f"🔴 [Anahtar {idx}] {masked} -> HATA: GEÇERSİZ ANAHTAR (API Key Invalid)")
                invalid_count += 1
            elif "503" in err or "UNAVAILABLE" in err:
                print(f"🟡 [Anahtar {idx}] {masked} -> YOĞUN: HİZMET GEÇİCİ OLARAK KULLANILAMIYOR (503 Service Unavailable)")
                overloaded_count += 1
            elif "429" in err or "Quota exceeded" in err:
                print(f"🟡 [Anahtar {idx}] {masked} -> LİMİT AŞILDI: KOTA / HIZ SINIRI (429 Rate Limit Exceeded)")
                overloaded_count += 1
            else:
                print(f"🔴 [Anahtar {idx}] {masked} -> BİLİNMEYEN HATA: {err[:80]}...")
                invalid_count += 1
                
    print("==================================================")
    print(f"📊 ÖZET: Canlı: {valid_count} | Hatalı/Geçersiz: {invalid_count} | Geçici Yoğun/Limitli: {overloaded_count}")
    print("==================================================")

if __name__ == "__main__":
    ping_api_keys()
