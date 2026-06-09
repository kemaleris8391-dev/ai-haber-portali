import sys
import os
import time
import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore

WEBHOOK_URL = "https://ai-haber-portali.vercel.app/api/webhook"
CHAT_ID = 933381040

def init_firestore():
    cred_path = r"c:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\backend-scripts\firebase_credentials.json"
    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")
    
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    return firestore.client()

def send_mock_webhook_message(text):
    print(f"Sending command mock: {text}")
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
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=15)
    print(f"Response Status Code: {response.status_code}")
    try:
        print(f"Response Body: {response.json()}")
    except:
        print(f"Response Text: {response.text[:200]}")
    return response.status_code == 200

def main():
    print("--- Telegram Webhook Detayli Ozellik Testi Baslatiliyor ---")
    
    # Sırasıyla en kısa süren işlemlerden en uzun sürene doğru komutları test edelim:
    
    # 1. /durum (Sistem Durumu) - Süre: ~0.8s
    print("\n[1/7] Sistem durumu sorgulaniyor (/durum)...")
    send_mock_webhook_message("/durum")
    time.sleep(2)
    
    # 2. /baslat ve /durdur (Otonom Ac/Kapat) - Süre: ~0.5s - 1.0s
    print("\n[2/7] Otonom ac/kapat test ediliyor...")
    send_mock_webhook_message("/durdur")
    time.sleep(2)
    send_mock_webhook_message("/baslat")
    time.sleep(2)

    # 3. /rss_liste (RSS Kaynaklari Listesi) - Süre: ~1.0s - 1.5s
    print("\n[3/7] RSS listesi sorgulaniyor (/rss_liste)...")
    send_mock_webhook_message("/rss_liste")
    time.sleep(2)
    
    # 4. /süre (Tarama Sikligi Menusu) - Süre: ~1.0s - 1.5s
    print("\n[4/7] Tarama sıklığı menüsü sorgulanıyor (/sure)...")
    send_mock_webhook_message("/sure")
    time.sleep(2)

    # 5. /ototemizlik (Ototemizlik Ayarlari) - Süre: ~1.2s - 2.0s
    print("\n[5/7] Ototemizlik menüsü sorgulanıyor (/ototemizlik)...")
    send_mock_webhook_message("/ototemizlik")
    time.sleep(2)
    
    # 6. /sil (Haber Silme Menusu) - Süre: ~1.5s - 2.5s (Sadece menü tetiği)
    print("\n[6/7] Haber silme menüsü sorgulanıyor (/sil)...")
    send_mock_webhook_message("/sil")
    time.sleep(2)

    # 7. /yardim (Ana Yardim Menusu) - Süre: ~1.5s - 2.5s
    print("\n[7/7] Genel yardım menüsü sorgulanıyor (/yardim)...")
    send_mock_webhook_message("/yardim")
    
    print("\n--- Tum komutların webhook simülasyon testleri başarıyla gönderildi. ---")

if __name__ == "__main__":
    main()
