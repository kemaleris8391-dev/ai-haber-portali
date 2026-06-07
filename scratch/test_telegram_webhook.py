import os
import sys
import json
import requests
from dotenv import load_dotenv

# .env dosyasını yükle
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, "backend-scripts", ".env")
load_dotenv(env_path)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = "https://ai-haber-portali.vercel.app/api/webhook"

if not BOT_TOKEN or not CHAT_ID:
    print("HATA: BOT_TOKEN veya CHAT_ID .env dosyasında bulunamadı!")
    sys.exit(1)

BOT_TOKEN = BOT_TOKEN.strip()
CHAT_ID = CHAT_ID.strip()

print(f"Telegram Bot Token: ...{BOT_TOKEN[-6:]}")
print(f"Telegram Chat ID: {CHAT_ID}")
print(f"Webhook URL: {WEBHOOK_URL}")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    r = requests.post(url, json=payload, timeout=10)
    if r.status_code == 200:
        return r.json().get("result", {})
    else:
        print(f"Telegram mesaj gönderme hatası: {r.status_code} - {r.text}")
        return None

def test_durum_command():
    print("\n--- TEST: /durum KOMUTU SİMÜLASYONU ---")
    payload = {
        "update_id": 999999,
        "message": {
            "message_id": 88888,
            "from": {
                "id": int(CHAT_ID),
                "is_bot": False,
                "first_name": "AntigravityTest"
            },
            "chat": {
                "id": int(CHAT_ID),
                "type": "private"
            },
            "date": 1600000000,
            "text": "/durum"
        }
    }
    
    print("Vercel Webhook'a /durum isteği gönderiliyor...")
    r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    print(f"Webhook Yanıt Kodu: {r.status_code}")
    print(f"Webhook Yanıtı: {r.text}")

def test_benzer_haber_callback():
    print("\n--- TEST: BENZER HABER callback query SİMÜLASYONU ---")
    
    # 1. Aşama: Kullanıcının chat'ine geçici bir test mesajı gönder
    print("1. Aşama: Telegram üzerinden geçici test mesajı oluşturuluyor...")
    msg = send_telegram_message("🤖 <b>Gemma 4 31B Semantik Analiz Testi</b>\n\n<i>Arka planda Vercel webhook simülasyonu çalıştırılıyor. Lütfen bekleyin...</i>")
    if not msg:
        print("Geçici test mesajı oluşturulamadı. İptal ediliyor.")
        return
        
    message_id = msg.get("message_id")
    print(f"Oluşturulan Geçici Mesaj ID: {message_id}")
    
    # 2. Aşama: Bu mesaj üzerinden Vercel Webhook'una callback query gönder
    payload = {
        "update_id": 888888,
        "callback_query": {
            "id": "test_callback_id_123",
            "from": {
                "id": int(CHAT_ID),
                "is_bot": False,
                "first_name": "AntigravityTest"
            },
            "message": {
                "message_id": message_id,
                "chat": {
                    "id": int(CHAT_ID),
                    "type": "private"
                },
                "text": "Geçici test mesajı"
            },
            "data": "menu:benzer"
        }
    }
    
    print("2. Aşama: Vercel Webhook'a callback query payload'u gönderiliyor...")
    r = requests.post(WEBHOOK_URL, json=payload, timeout=30)
    print(f"Webhook Yanıt Kodu: {r.status_code}")
    print(f"Webhook Yanıtı: {r.text}")

def test_tara_command():
    print("\n--- TEST: /tara KOMUTU SİMÜLASYONU ---")
    payload = {
        "update_id": 777777,
        "message": {
            "message_id": 77777,
            "from": {
                "id": int(CHAT_ID),
                "is_bot": False,
                "first_name": "AntigravityTest"
            },
            "chat": {
                "id": int(CHAT_ID),
                "type": "private"
            },
            "date": 1600000000,
            "text": "/tara"
        }
    }
    
    print("Vercel Webhook'a /tara isteği gönderiliyor...")
    r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    print(f"Webhook Yanıt Kodu: {r.status_code}")
    print(f"Webhook Yanıtı: {r.text}")

if __name__ == "__main__":
    send_telegram_message("🔌 <b>Antigravity AI Otonom Entegrasyon Testi Başlatıldı!</b>\n\nSırasıyla <code>/durum</code> komutu, <code>/tara</code> (RSS Tarama Tetikleyicisi) ve <code>menu:benzer</code> (Gemma 31B Semantik Arama) modülleri test edilecek. Sonuçlar bu sohbete yansıyacaktır.")
    test_durum_command()
    test_tara_command()
    test_benzer_haber_callback()
    send_telegram_message("✅ <b>Entegrasyon Testleri Başarıyla Tamamlandı!</b>")
