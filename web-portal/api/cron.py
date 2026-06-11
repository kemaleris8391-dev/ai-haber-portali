import os
import json
import time
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler
import requests
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase Firestore client initialization
db_client = None

def init_firebase():
    global db_client
    if db_client is not None:
        return db_client

    try:
        app = firebase_admin.get_app()
    except ValueError:
        cred_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if cred_env:
            try:
                cred_dict = json.loads(cred_env)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"HATA: FIREBASE_SERVICE_ACCOUNT_JSON ayrıştırılamadı: {e}")
                firebase_admin.initialize_app()
        else:
            firebase_admin.initialize_app()

    db_client = firestore.client()
    return db_client

def get_scheduler_config():
    db = init_firebase()
    doc_ref = db.collection("system_config").document("scheduler")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        interval = data.get("interval_minutes", 20)
        last_run = data.get("last_run_time", time.time())
        is_running = data.get("is_running", False)
        is_active = data.get("is_active", True)
        return {
            "interval_minutes": int(interval),
            "last_run_time": float(last_run),
            "is_running": bool(is_running),
            "is_active": bool(is_active)
        }
    else:
        default_config = {
            "interval_minutes": 20,
            "last_run_time": time.time(),
            "is_running": False,
            "is_active": True
        }
        doc_ref.set(default_config)
        return default_config

def update_scheduler_config(interval_minutes=None, last_run_time=None, is_running=None, is_active=None):
    db = init_firebase()
    doc_ref = db.collection("system_config").document("scheduler")
    
    update_data = {}
    if interval_minutes is not None:
        update_data["interval_minutes"] = int(interval_minutes)
    if last_run_time is not None:
        update_data["last_run_time"] = float(last_run_time)
    if is_running is not None:
        update_data["is_running"] = bool(is_running)
    if is_active is not None:
        update_data["is_active"] = bool(is_active)
        
    if update_data:
        doc_ref.update(update_data)

def get_publish_timer_config():
    """Gets publish timer config from Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("publish_timer")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        return {
            "delay_minutes": int(data.get("delay_minutes", 0)),
            "timer_start_time": float(data.get("timer_start_time", 0.0)),
            "next_publish_time": float(data.get("next_publish_time", 0.0))
        }
    else:
        default_config = {
            "delay_minutes": 0,
            "timer_start_time": 0.0,
            "next_publish_time": 0.0
        }
        doc_ref.set(default_config)
        return default_config

def update_publish_timer_config(delay_minutes=None, timer_start_time=None, next_publish_time=None):
    """Updates publish timer config in Firestore."""
    db = init_firebase()
    doc_ref = db.collection("system_config").document("publish_timer")
    
    update_data = {}
    if delay_minutes is not None:
        update_data["delay_minutes"] = int(delay_minutes)
    if timer_start_time is not None:
        update_data["timer_start_time"] = float(timer_start_time)
    if next_publish_time is not None:
        update_data["next_publish_time"] = float(next_publish_time)
        
    if update_data:
        doc_ref.set(update_data, merge=True)

def send_message(text):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram mesaj gönderme hatası: {e}")

def trigger_github_workflow(research=False):
    github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    owner = "kemaleris8391-dev"
    repo = "ai-haber-portali"
    workflow_id = "autonomous_rss.yml"
    
    if not github_token:
        err_msg = "❌ <b>HATA: GITHUB_PAT bulunamadı.</b> Otonom tetikleme yapılamadı. Lütfen Vercel panelinden GITHUB_PAT ortam değişkenini tanımlayın."
        print(err_msg)
        send_message(err_msg)
        return False
        
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"Bearer {github_token.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AIHABERLER-Bot"
    }
    data = {
        "ref": "main",
        "inputs": {
            "force": "true",
            "research": "true" if research else "false"
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 204:
            send_message("⚡ <b>Bulut Yazarı Otonom Zamanlayıcı (Vercel Cron)</b> uyanma zamanınızın geldiğini tespit etti ve GitHub Actions sunucusunu <b>otomatik olarak tetikledi!</b>\n\n🔍 Taramalar yapılıyor...")
            
            # Quota/Billing check (Wait 3 seconds and query latest run to see if it immediately failed)
            time.sleep(3)
            runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?per_page=1"
            runs_res = requests.get(runs_url, headers=headers, timeout=10)
            if runs_res.status_code == 200:
                runs = runs_res.json().get("workflow_runs", [])
                if runs:
                    latest_run = runs[0]
                    status = latest_run.get("status")
                    conclusion = latest_run.get("conclusion")
                    html_url = latest_run.get("html_url", "")
                    
                    # Eğer çalışma anında completed ve başarısız/iptal olduysa
                    if status == "completed" and conclusion in ["failure", "cancelled", "skipped"]:
                        send_message(
                            f"❌ <b>GitHub Actions Başlatılamadı!</b>\n"
                            f"Çalışma hemen sonlandırıldı (Muhtemelen <b>GitHub Actions aylık kullanım kotanız doldu</b> veya faturalandırma limitiniz yetersiz).\n\n"
                            f"• Durum: <code>{status}</code>\n"
                            f"• Sonuç: <code>{conclusion}</code>\n"
                            f"👉 <a href='{html_url}'>GitHub'da İncele</a>"
                        )
                        return False
            return True
        else:
            err_msg = f"❌ <b>GitHub API Tetikleme Hatası!</b>\nAPI Yanıt Kodu: {response.status_code}\nDetay: {response.text[:250]}"
            print(err_msg)
            send_message(err_msg)
            return False
    except Exception as e:
        err_msg = f"❌ <b>GitHub Actions Bağlantı Hatası!</b>\nDetay: {str(e)}"
        print(err_msg)
        send_message(err_msg)
        return False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Processes incoming Vercel Cron GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.end_headers()
        
        try:
            # 0. Yayınlama Zamanlayıcı (publish_timer) Kontrolü
            try:
                timer_conf = get_publish_timer_config()
                delay_val = timer_conf.get("delay_minutes", 0)
                timer_start_val = timer_conf.get("timer_start_time", 0.0)
                next_publish_val = timer_conf.get("next_publish_time", 0.0)
                
                now = time.time()
                
                if delay_val > 0 and timer_start_val > 0.0 and now >= next_publish_val:
                    print("Yayın zamanlayıcı süresi doldu! Toplu yayın tetikleniyor...")
                    update_publish_timer_config(timer_start_time=0.0, next_publish_time=0.0)
                    
                    success = trigger_github_workflow()
                    if success:
                        update_scheduler_config(last_run_time=now, is_running=False)
                        send_message(
                            "⏱️ <b>Toplu Yayınlama Süresi Doldu!</b>\n\n"
                            f"Seçtiğiniz <b>{delay_val} dakikalık</b> bekleme süresi sona erdi. "
                            "Görüş yazdığınız tüm haberlerin yayına alınması için bulut derleyicisi tetiklendi."
                        )
                        self.wfile.write(json.dumps({"status": "publish_timer_triggered", "delay": delay_val}).encode())
                        return
            except Exception as timer_err:
                print(f"Cron Publish Timer Hatası: {timer_err}")

            # 1. Zamanlayıcı ayarlarını oku
            sched_conf = get_scheduler_config()
            is_active_val = sched_conf.get("is_active", True)
            interval_val = sched_conf["interval_minutes"]
            last_run_val = sched_conf["last_run_time"]
            is_running_val = sched_conf["is_running"]
            
            now = time.time()
            elapsed_min = (now - last_run_val) / 60.0
            
            print(f"Cron Çalıştı. Son çalışmadan bu yana geçen süre: {elapsed_min:.2f} dakika. Beklenen aralık: {interval_val} dakika. Aktif mi: {is_active_val}")
            
            # Eğer pasif ise tetikleme yapma
            if not is_active_val:
                print("Zamanlayıcı pasif durumda. Tetikleme atlanıyor.")
                self.wfile.write(json.dumps({"status": "inactive", "elapsed": elapsed_min}).encode())
                return
            
            # 2. Süre kontrolü
            if elapsed_min >= interval_val:
                # Kilit kontrolü (Eğer 15 dakikadan uzun süredir kilitliyse kilidi yok say)
                if not is_running_val or elapsed_min >= 15.0:
                    print("Süre doldu, otonom tetikleme başlatılıyor...")
                    update_scheduler_config(is_running=True)
                    
                    success = trigger_github_workflow()
                    if success:
                        # Update last_run_time immediately to prevent 10-minute retry spam!
                        update_scheduler_config(last_run_time=time.time(), is_running=False)
                        self.wfile.write(json.dumps({"status": "triggered", "elapsed": elapsed_min}).encode())
                    else:
                        # Deactivate scheduler to prevent spam loops on system error/quota limit
                        update_scheduler_config(is_running=False, is_active=False)
                        send_message(
                            "⏸️ <b>Otonom Zamanlayıcı Durduruldu!</b>\n"
                            "Tetikleme veya bulut çalışması başarısız olduğu için sistem üst üste spam yapmaması amacıyla otonom zamanlayıcıyı otomatik olarak <b>pasif moda</b> aldı.\n\n"
                            "<i>Sorunu giderdikten sonra bot menüsünden otonomu tekrar aktif edebilirsiniz.</i>"
                        )
                        self.wfile.write(json.dumps({"status": "failed to trigger", "elapsed": elapsed_min}).encode())
                else:
                    print("Zorlama bypass edildi: Başka bir tarama şu anda aktif.")
                    self.wfile.write(json.dumps({"status": "already running", "elapsed": elapsed_min}).encode())
            else:
                remaining = int(interval_val - elapsed_min)
                print(f"Otonom tarama için henüz süre dolmadı. Kalan: {remaining} dakika.")
                self.wfile.write(json.dumps({"status": "waiting", "remaining_minutes": remaining}).encode())
                
        except Exception as err:
            print(f"Cron Genel Hatası: {err}")
            self.wfile.write(json.dumps({"status": "error", "error": str(err)}).encode())
