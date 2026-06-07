FROM python:3.11-slim

WORKDIR /app

# Gerekli sistem paketlerini kur
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
# Docker context backend-scripts olarak ayarlanacağı için sadece o dizindekileri kopyalayacak
COPY . .

# Botu çalıştır
CMD ["python", "telegram_bot.py"]
