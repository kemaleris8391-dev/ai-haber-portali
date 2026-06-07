import argparse
import sys
import os
from dotenv import load_dotenv

# backend-scripts dizinini ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from telegram_notifier import send_error, send_success

def main():
    load_dotenv(override=True)
    
    parser = argparse.ArgumentParser(description="Pipeline durumunu Telegram'a bildirir.")
    parser.add_argument("--status", choices=["success", "fail"], required=True, help="İşlem durumu")
    parser.add_argument("--step", choices=["build", "deploy", "general"], required=True, help="Pipeline adımı")
    parser.add_argument("--error", type=str, default="", help="Hata detayı (fail durumunda)")
    
    args = parser.parse_args()
    
    if args.status == "fail":
        step_names = {
            "build": "Astro Statik Site Derleme Hatası (Build)",
            "deploy": "Firebase Hosting Dağıtım Hatası (Deploy)",
            "general": "Haber Portalı Genel Akış Hatası"
        }
        title = step_names.get(args.step, "Pipeline Hatası")
        error_detail = args.error if args.error else "Bilinmeyen bir hata oluştu."
        success = send_error(title, error_detail)
        if success:
            print("Hata bildirimi Telegram'a gönderildi.")
        else:
            print("Telegram bildirimi gönderilemedi.")
            
    elif args.status == "success":
        step_names = {
            "build": "Web sitesi başarıyla derlendi.",
            "deploy": "Web sitesi başarıyla Firebase'e yüklendi ve yayına alındı!",
            "general": "Haber portalı akışı başarıyla tamamlandı!"
        }
        title = "Haber Portalı Güncellendi"
        details = step_names.get(args.step, "İşlem başarıyla tamamlandı.")
        if args.step == "deploy":
            details += "\n👉 Canlı Adres: https://aihaberler.web.app"
            
            # Google WebSub (PubSubHubbub) Ping
            try:
                import requests
                print("Google WebSub Hub'ina yeni surum yayini bildiriliyor (Ping)...")
                response = requests.post(
                    "https://pubsubhubbub.appspot.com/",
                    data={
                        "hub.mode": "publish",
                        "hub.url": "https://aihaberler.web.app/rss.xml"
                    },
                    timeout=10
                )
                if response.status_code in [200, 204]:
                    print("Basarili: WebSub bildirimi basariyla gonderildi.")
                    details += "\n📡 WebSub: Google Hub basariyla tetiklendi."
                else:
                    print(f"Uyari: WebSub Hub {response.status_code} koduyla yanit verdi: {response.text}")
                    details += f"\n📡 WebSub Uyarisi: Hub durum kodu {response.status_code}"
            except Exception as e:
                print(f"Hata: WebSub ping istegi basarisiz: {e}")
                details += f"\n📡 WebSub Hatasi: {e}"
            
        success = send_success(title, details)
        if success:
            print("Başarı bildirimi Telegram'a gönderildi.")
        else:
            print("Telegram bildirimi gönderilemedi.")

if __name__ == "__main__":
    main()
