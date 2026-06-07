import os
import sys
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv(override=True)

# API Anahtarlarını al
API_KEYS = []
keys_str = os.getenv("GEMINI_API_KEYS")
if keys_str:
    API_KEYS = [k.strip() for k in keys_str.split(",") if k.strip()]

current_key_idx = 0

def get_next_client():
    global current_key_idx
    if not API_KEYS:
        fallback_key = os.getenv("GEMINI_API_KEY")
        if fallback_key:
            return genai.Client(api_key=fallback_key.strip())
        return genai.Client()
    api_key = API_KEYS[current_key_idx]
    return genai.Client(api_key=api_key)

def rotate_key():
    global current_key_idx
    if API_KEYS:
        current_key_idx = (current_key_idx + 1) % len(API_KEYS)

def check_batch_with_llm(batch_data, model_name="gemma-4-31b-it"):
    prompt = f"""
Aşağıda verilen haber paketini (JSON formatında) analiz et. Her bir haberin portalımızın yayın politikasına uygun olup olmadığını ve mükerrer (kopya) olup olmadığını belirle.

Yayın Politikası Odak Alanları:
- Sadece teknoloji, bilimsel buluşlar, oyun dünyası, geek dizileri/filmleri (bilim kurgu, fantastik, oyun uyarlamaları, sinema teknolojileri) ve kuantum dünyası/bilgisayarları hakkında olmalıdır.

Politika Dışı (Uygun Olmayan) Alanlar:
- Siyaset, politika, standart aşk/dram dizileri, magazin haberleri, genel otomotiv incelemeleri (elektrikli/otonom teknolojiler dışındaki standart araçlar), genel borsa/finans, yasal ihtilaflar, yemek tarifi vb.

Mükerrerlik Kuralları:
- Aynı konuyu veya olayı anlatan haberler mükerrerdir. En eski veya ana haberi temel kabul edip diğer mükerrer haberlerin hangisi olduğunu belirle (duplicate_of alanına ana haberin dosya adını yaz).

Verilen Haber Listesi (JSON):
{json.dumps(batch_data, ensure_ascii=False, indent=2)}

Çıktıyı KESİNLİKLE aşağıdaki JSON formatında ver (başka açıklama ekleme):
{{
  "results": [
    {{
      "filename": "haber-dosya-adi.md",
      "is_compliant": true,
      "reason": "Uygundur gerekçesi veya uygunsuzsa nedeni",
      "duplicate_of": "parent_filename.md"
    }}
  ]
}}
"""
    max_retries = len(API_KEYS) if API_KEYS else 3
    last_error = ""
    
    for attempt in range(max_retries):
        client = get_next_client()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            if response.text:
                try:
                    result = json.loads(response.text)
                    return result, model_name
                except Exception as parse_err:
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(clean_text)
                    return result, model_name
        except Exception as e:
            last_error = str(e)
            print(f"Hata (Deneme {attempt + 1}/{max_retries}): {last_error}")
            rotate_key()
            if "429" in last_error:
                time.sleep(2)
                
    raise Exception(f"Tüm denemeler hata verdi. Son Hata: {last_error}")

def main():
    snippets_file = 'backend-scripts/news_snippets.json'
    if not os.path.exists(snippets_file):
        snippets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'news_snippets.json')
        
    with open(snippets_file, 'r', encoding='utf-8') as f:
        posts = json.load(f)
        
    total_posts = len(posts)
    print(f"Toplam {total_posts} haber analiz edilecek (Model: gemma-4-31b-it).")
    
    batch_size = 25
    batches = [posts[i:i + batch_size] for i in range(0, total_posts, batch_size)]
    
    start_time = time.time()
    all_results = []
    
    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)} gönderiliyor ({len(batch)} haber)...")
        batch_start = time.time()
        try:
            result, used_model = check_batch_with_llm(batch, model_name="gemma-4-31b-it")
            batch_time = time.time() - batch_start
            print(f"Batch {i} tamamlandı. Süre: {batch_time:.2f} saniye.")
            if "results" in result:
                all_results.extend(result["results"])
        except Exception as e:
            print(f"Batch {i} işlenirken hata oluştu: {e}")
            
    total_time = time.time() - start_time
    
    print("\n--- GEMMA-4-31B-IT ANALİZ ÖZETİ ---")
    print(f"Toplam Haber Sayısı: {total_posts}")
    print(f"Toplam Geçen Süre: {total_time:.2f} saniye")
    print(f"Haber Başına Ortalama Süre: {total_time / total_posts:.4f} saniye")

if __name__ == '__main__':
    main()
