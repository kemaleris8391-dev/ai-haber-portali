import sys
import os
import time
import requests
import json

# Canlı webhook URL'si
WEBHOOK_URL = "https://ai-haber-portali.vercel.app/api/webhook"
CHAT_ID = 933381040

def send_mock_webhook_message(text):
    print(f"\n[TEST] Komut/Mesaj Gönderiliyor: {text}")
    payload = {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time()) % 100000,
            "from": {
                "id": CHAT_ID,
                "is_bot": False,
                "first_name": "Kaose",
                "username": "kaose"
            },
            "chat": {
                "id": CHAT_ID,
                "type": "private"
            },
            "date": int(time.time()),
            "text": text
        }
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=20)
        print(f"-> Webhook Yanıt Kodu: {response.status_code}")
        try:
            print(f"-> Yanıt Gövdesi: {response.json()}")
        except:
            print(f"-> Yanıt Metni: {response.text[:300]}")
        return response.status_code == 200
    except Exception as e:
        print(f"-> İstek Hatası: {e}")
        return False

def main():
    print("==================================================")
    print("TELEGRAM BOTU WEBHOOK MOCK TESTİ BAŞLATILIYOR")
    print("==================================================")
    
    # 1. Aşama: Durum Sorgulama
    print("\n--- AŞAMA 1: Sistem Durum Raporu Sorgulama (/durum) ---")
    send_mock_webhook_message("/durum")
    time.sleep(3)
    
    # 2. Aşama: Manuel Taramayı Tetikleme
    print("\n--- AŞAMA 2: Manuel Tarama Tetikleme (/tara) ---")
    send_mock_webhook_message("/tara")
    time.sleep(3)
    
    # 3. Aşama: Özel Konu İle Taramayı Aktifleştirme (Kuyruğa Ekleme)
    topic = "Kuantum Bilgisayarlar ve Yapay Zekanın Geleceği"
    print(f"\n--- AŞAMA 3: Özel Konu Talebi Gönderme ({topic}) ---")
    send_mock_webhook_message(topic)
    time.sleep(3)
    
    # 4. Aşama: Ototemizlik Menüsünü Tetikleme
    print("\n--- AŞAMA 4: Ototemizlik Menüsünü Sorgulama (/ototemizlik) ---")
    send_mock_webhook_message("/ototemizlik")
    time.sleep(3)
    
    print("\n==================================================")
    print("MOCK TESTLER BAŞARIYLA TAMAMLANDI")
    print("==================================================")

if __name__ == "__main__":
    main()
