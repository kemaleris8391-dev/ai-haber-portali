import requests
import os
from dotenv import load_dotenv

# Load env variables
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(workspace_root, "backend-scripts", ".env")
load_dotenv(env_path, override=True)

api_key = os.getenv("PEXELS_API_KEY").split(',')[0].strip()
headers = {"Authorization": api_key}

queries = ["casper tablet", "casper pad m10 pro", "tablet writing", "tablet with stylus keyboard"]
for q in queries:
    url = f"https://api.pexels.com/v1/search?query={q}&per_page=5&orientation=landscape"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        photos = r.json().get("photos", [])
        print(f"Sorgu: '{q}' | Sonuç Adedi: {len(photos)}")
        if photos:
            print(f"  İlk Fotoğraf ID: {photos[0]['id']}, URL: {photos[0]['src']['large2x']}")
    else:
        print(f"Sorgu: '{q}' | Hata Kodu: {r.status_code}")
