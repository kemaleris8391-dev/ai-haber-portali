import os
import requests
from dotenv import load_dotenv

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(workspace_root, "backend-scripts", ".env")
load_dotenv(env_path, override=True)

api_keys_str = os.getenv("PEXELS_API_KEY")
api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
headers = {"Authorization": api_keys[0]}

url = 'https://api.pexels.com/v1/search?query=samsung galaxy fold device concept table&per_page=15&orientation=landscape'
r = requests.get(url, headers=headers).json()
photo = r['photos'][5]
img_r = requests.get(photo['src']['large2x'])

img_path = os.path.join(workspace_root, "web-portal", "public", "images", "news", "katlanabilir-telefonlarda-yeni-zirve-samsung-galaxy-z-fold-8.jpg")
with open(img_path, 'wb') as f:
    f.write(img_r.content)
print("SUCCESS LAST FIXED")
