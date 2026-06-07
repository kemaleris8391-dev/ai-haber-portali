import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import firebase_helper

def test():
    try:
        print("Firestore bağlantısı test ediliyor...")
        config = firebase_helper.get_scheduler_config()
        print("Firestore Bağlantısı BAŞARILI!")
        print("Mevcut Zamanlayıcı Ayarları:")
        print(f"- Sıklık: {config['interval_minutes']} dakika")
        print(f"- Son Tarama: {config['last_run_time']}")
        print(f"- Aktif mi: {config['is_running']}")
    except Exception as e:
        print(f"Firestore Bağlantı HATASI: {e}")
        print("\nİpucu: Firebase CLI yetkilendirmesi eksik olabilir veya firebase_credentials.json dosyası bulunamadı.")

if __name__ == "__main__":
    test()
