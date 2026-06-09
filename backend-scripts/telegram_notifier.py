import os
import requests
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv(override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    """Belirtilen Telegram Chat ID'sine HTML formatında mesaj gönderir."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("UYARI: Telegram Bot Token veya Chat ID .env dosyasında tanımlı değil. Bildirim gönderilemedi.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID.strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"Hata: Telegram API yanıtı başarısız. Kod: {response.status_code}, Detay: {response.text}")
            return False
    except Exception as e:
        print(f"Hata: Telegram mesajı gönderilemedi. Detay: {e}")
        return False

def send_error(error_title, error_detail):
    """Detaylı hata bildirimini Telegram'a kod bloğu ile birlikte gönderir."""
    emoji = "🚨"
    message = (
        f"{emoji} <b>{error_title}</b>\n\n"
        f"<b>Hata Detayı:</b>\n"
        f"<code>{error_detail}</code>"
    )
    return send_message(message)

def send_success(success_title, details=""):
    """Başarı mesajını Telegram'a gönderir."""
    emoji = "✅"
    message = f"{emoji} <b>{success_title}</b>\n"
    if details:
        message += f"\n{details}"
    return send_message(message)

def send_pending_post_notification(title, summary, category, doc_id):
    """Yayın onayı bekleyen haber bildirimini satır içi butonlarla gönderir ve message_id döner."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("UYARI: Telegram Bot Token veya Chat ID .env dosyasında tanımlı değil.")
        return None
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN.strip()}/sendMessage"
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🗑️ İptal Et / Sil", "callback_data": f"approve_delete:{doc_id}"}
            ]
        ]
    }
    
    text = (
        f"📝 <b>Yayın Onayı Bekleyen Haber</b>\n\n"
        f"📂 <b>Kategori:</b> {category}\n"
        f"📰 <b>Başlık:</b> {title}\n"
        f"🔍 <b>Özet:</b> {summary}\n\n"
        f"✍️ Bu habere kendi görüşünüzü ekleyip yayınlamak için <b>bu mesaja YANIT (Reply) yazıp gönderin</b>.\n\n"
        f"🗑️ Haberi tamamen silmek/iptal etmek için aşağıdaki butonu kullanabilirsiniz."
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID.strip(),
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            return res_json.get("result", {}).get("message_id")
        else:
            print(f"Hata: Telegram API yanıtı başarısız. Kod: {response.status_code}, Detay: {response.text}")
    except Exception as e:
        print(f"Hata: Telegram mesajı gönderilemedi. Detay: {e}")
    return None
