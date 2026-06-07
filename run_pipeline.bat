@echo off
CHCP 65001 > NUL
setlocal enabledelayedexpansion

echo ===================================================
echo   OTONOM HABER PORTALI ENTEGRASYON PIPELINE
echo ===================================================

:: 1. Çalışma Dizinleri Tanımları
set "BASE_DIR=%~dp0"
set "BACKEND_DIR=%BASE_DIR%backend-scripts"
set "WEB_DIR=%BASE_DIR%web-portal"

:: 2. Backend İşlemleri (Python Haber Çekme ve AI Yazıcı)
echo.
echo [1/3] Python Backend Çalıştırılıyor...
cd /d "%BACKEND_DIR%"

:: Sanal ortam kontrolü ve kurulumu
if not exist venv (
    echo Python sanal ortamı (venv) oluşturuluyor...
    python -m venv venv
)

:: Sanal ortamı aktif et
call venv\Scripts\activate.bat

:: Bağımlılıkları kontrol et/yükle
echo Bağımlılıklar kontrol ediliyor...
pip install -r requirements.txt > nul

:: Gemini API Key kontrolü
if "%GEMINI_API_KEY%"=="" (
    if exist .env (
        echo .env dosyasından GEMINI_API_KEY okunuyor...
        for /f "usebackq tokens=1,2 delims==" %%i in (".env") do (
            if "%%i"=="GEMINI_API_KEY" set "GEMINI_API_KEY=%%j"
        )
    )
)

if "%GEMINI_API_KEY%"=="" (
    echo [HATA] GEMINI_API_KEY ortam değişkeni veya .env dosyasında bulunamadı!
    echo Lütfen backend-scripts klasörü içinde .env dosyası oluşturun ve GEMINI_API_KEY=api_key şeklinde girin.
    if not "%1"=="--silent" pause
    exit /b 1
)

:: Firestore'dan güncel ayarları ve promptları çek
echo Firestore'dan güncel ayarlar ve promptlar indiriliyor...
python export_env_from_firestore.py
if %ERRORLEVEL% NEQ 0 (
    echo [UYARI] Firestore'dan güncel ayarlar indirilemedi, mevcut yerel dosyalarla devam ediliyor.
)

:: Ana betiği çalıştır
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo [HATA] Python betiği çalışırken bir sorun oluştu.
    if not "%1"=="--silent" pause
    exit /b 1
)

deactivate

:: 3. Web Arayüzü Build İşlemleri (Astro SSG Derleme)
echo.
echo [2/3] Astro Web Sitesi Derleniyor (Static Site Generation)...
cd /d "%WEB_DIR%"

:: Node_modules kontrolü
if not exist node_modules (
    echo npm bağımlılıkları eksik. Yükleniyor...
    call npm install
)

:: Astro projesini build et
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [HATA] Astro build işlemi başarısız oldu.
    call "%BACKEND_DIR%\venv\Scripts\python.exe" "%BACKEND_DIR%\notify_pipeline_status.py" --status fail --step build --error "Astro statik site derleme (build) islemi sirasinda hata olustu. Console loglarini kontrol edin."
    if not "%1"=="--silent" pause
    exit /b 1
)

:: 4. Firebase Hosting Deployment
echo.
echo [3/3] Firebase Dağıtım Adımı...
if exist firebase.json (
    echo Siteniz Firebase Hosting'e yükleniyor...
    call npx firebase-tools deploy --only hosting
    if !ERRORLEVEL! NEQ 0 (
        echo [HATA] Firebase dağıtımı başarısız oldu.
        call "%BACKEND_DIR%\venv\Scripts\python.exe" "%BACKEND_DIR%\notify_pipeline_status.py" --status fail --step deploy --error "Firebase hosting'e yukleme yapilirken hata olustu. Console loglarini kontrol edin."
        if not "%1"=="--silent" pause
        exit /b 1
    )
) else (
    echo Firebase yapılandırması henüz tamamlanmadı, dağıtım adımı atlandı.
)

:: Başarı bildirimi gönder
call "%BACKEND_DIR%\venv\Scripts\python.exe" "%BACKEND_DIR%\notify_pipeline_status.py" --status success --step deploy

echo.
echo ===================================================
echo   İŞLEM TAMAMLANDI! Haberler başarıyla yayınlandı.
echo ===================================================
cd /d "%BASE_DIR%"
if not "%1"=="--silent" pause
