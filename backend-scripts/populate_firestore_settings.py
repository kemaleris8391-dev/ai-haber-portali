import os
import sys
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dotenv import load_dotenv

# Windows CP1254 terminal emoji encoding fix
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# .env dosyasından gelen Firebase Credentials
load_dotenv(override=True)

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "backend-scripts/firebase_credentials.json"))
        firebase_admin.initialize_app(cred)
    return firestore.client()

def populate_firestore():
    db = initialize_firebase()

    print("Firestore veritabanı güncelleniyor...")

    # 1. Site Ayarları
    site_settings_ref = db.collection('system_config').document('site_settings')
    site_settings_ref.set({
        "PUBLIC_BRAND_NAME": "AIHABERLER",
        "PUBLIC_CONTACT_EMAIL": "kemaleris8391@gmail.com",
        "PUBLIC_SITE_URL": "https://aihaberler.web.app"
    })
    print("✅ Site ayarları eklendi.")

    # 2. Gemini Promptları (E-E-A-T & Google Discover & AdSense Uyumlu)
    
    rewrite_prompt = """Aşağıdaki haber başlığı ve özetini analiz et. Bu haberi tamamen özgün, Türkçe, akıcı, SEO dostu ve profesyonel bir teknoloji/oyun/sinema editörü üslubuyla yeniden yaz. 

Yazım Tarzı ve Doğruluk Kuralları (MANDATORY):
1. **İlgi Çekici ve Sürükleyici Dil:** Donuk ve makine dili yerine okuyucunun dikkatini ilk cümleden yakalayan, canlı, dinamik ve profesyonel bir üslup kullan.
2. **Konuda Tutucu (Strict Focus):** Haberin odağından kesinlikle sapma. Girdi olarak verilen konunun dışına çıkma, konuyu gereksiz yere dağıtma veya alakasız teknolojilerden bahsetme. Sadece haberin ana konusuna derinlemesine ve tutarlı bir şekilde odaklan.
3. **KESİNLİKLE YALAN HABER YAPMA (Zero Fabrication):** Asla uydurma veriler, uydurma tarihler, hayali kaynaklar veya yanlış iddialar üretme. Girdi haberinde yer alan gerçek olgulara ve doğrulanabilir verilere %100 sadık kal.
4. **Clickbait Olmayan Merak Uyandırıcı Başlık:** Clickbait (tık tuzağı veya aldatıcı) olmayan ama merak uyandıran, profesyonel, okuma potansiyeli yüksek Türkçe başlıklar oluştur.
5. **Türkçe Dil ve Çeviri Hassasiyeti:** Girdi haber başlığı veya özeti İngilizce (veya başka bir dilde) ise, haberi anlam kaybı olmadan tamamen Türkçe diline çevirip yeniden yaz. Gerekli yerlerde veya teknik terminolojide (örneğin "CPU", "ray tracing", "pipeline" gibi) İngilizce terimleri olduğu gibi kullanabilirsin ancak haberin genel dili akıcı, anlaşılır ve tamamen Türkçe olmalıdır.

Hayati Güvenlik ve İçerik Kuralları (MANDATORY):
1. KESİNLİKLE siyaset, politika, devletlerarası krizler, dini konular, toplumsal tartışmalar, yasal ihtilaflar, kişisel karalamalar veya suçlamalar gibi hassas ve yasal risk barındıran konulara girme.
2. Haberlerin odağı sadece saf teknoloji, bilimsel buluşlar, oyun güncellemeleri, yeni dizi/film duyuruları, fragmanlar ve kuantum fiziği/bilgisayarları/teknolojileri olmalıdır.
3. Dizi-Film kategorisi altındaki haberler SADECE bilim kurgu, fantastik, oyun uyarlamaları, dijital yayın teknolojileri (Netflix/Disney+ vb. teknik haberleri) veya sinemada yapay zeka/CGI kullanımıyla ilgili olmalıdır. Yerel/standart aşk dizileri, magazin haberleri, alakasız dram veya genel sinema dedikoduları KESİNLİKLE haber yapılmamalıdır.
4. EĞER GİRDİ HABERİ BU BELİRTİLEN SINIRLARIN (Teknoloji, Oyun, Bilim, Kuantum, Geek Dizi/Film) DIŞINDAYSA, kesinlikle makale yazma ve sadece aşağıdaki hata formatında JSON dön:
{
  "error": "Bu konu/haber portalımızın odak alanı (Teknoloji, Oyun, Bilim Kurgu/Geek Dizi-Film, Kuantum) dışındadır."
}
5. Suya sabuna dokunmayan, tamamen tarafsız, objektif, yasal açıdan %100 güvenli, sadece bilgilendirici ve nötr bir dil kullan.
6. Kaynak haberde politik veya hukuki bir tartışma/polemik varsa, bu kısımları tamamen temizle ve konuyu yalnızca nesnel teknolojik/endüstriyel boyutuyla ele al.

Genel Yapı & E-E-A-T Katma Değer Kuralları:
1. Haber içeriği en az 4 paragraflık, kapsamlı ve doyurucu bir teknik inceleme/makale metni olmalıdır.
2. Metin içinde kesinlikle en az 2 adet analitik alt başlık (markdown ## olarak) kullanılmalıdır. Haber konusuyla en iyi eşleşen iki başlığı seçerek metne entegre et:
   - ## Teknolojik Altyapı ve Yenilikler (Teknik detaylar, mimari, kullanılan yenilikçi yöntemler)
   - ## Sektörel Etki ve Pazar Analizi (Rakiplerle karşılaştırma, endüstri üzerindeki kısa/uzun vadeli etkileri)
   - ## Kullanıcı Deneyimi ve Gelecek Öngörüsü (Tüketicinin veya oyuncunun elde edeceği fayda, gelecekteki olası gelişmeler)
   - ## Eleştirel Bakış ve Soru İşaretleri (Varsa olumsuz yönler, güvenlik riskleri veya cevaplanmamış sorular)
3. Haberin en sonuna mutlaka "### Editörün Kaleminden" başlığı altında, okuyucuyla bağ kuran, samimi, objektif ve zenginleştirici 2-3 cümlelik derinlemesine bir değerlendirme ekle.
4. "Editörün Kaleminden" paragrafının BİTİMİNDE, haberin orijinal kaynağını kesinlikle şu Markdown formatında ekle: `[Haberin Orijinal Kaynağı: {source_name}]({raw_link})`. Kaynak linki için asla "Link burada", "haberin devamı" gibi ifadeler kullanma.
5. Haber için en fazla 160 karakterlik bir SEO meta açıklaması (description) oluştur.
6. Haberle ilgili 5 adet Türkçe etiket (keywords) belirle.
7. Pexels görsel arama motoru için haberin ana konusunu, markasını ve modelini içeren İngilizce 2-3 kelimelik net ve nokta atışı bir görsel arama sorgusu (pexels_query) yaz. Örnek: "playstation 5 console" (sadece "playstation" yazma), "intel arc gpu" (sadece "gpu" yazma), "quantum computing chip" (sadece "quantum" yazma), "volkswagen ID electric car" (sadece "car" yazma).

Girdi Haber Başlığı: {raw_title}
Girdi Haber Özeti: {raw_summary}
Haber Kategorisi: {category}

Çıktıyı aşağıdaki JSON formatında ver (Hata durumunda yukarıdaki hata JSON formatını kullanın):
{
  "title": "...",
  "content": "...",
  "description": "...",
  "keywords": ["tag1", "tag2", ...],
  "image_prompt": "A detailed 3D concept render of the topic",
  "pexels_query": "..."
}
"""

    semantic_duplicates_prompt = """Aşağıda sitemizde son 24 saatte yayınlanmış olan haberlerin başlıkları (Mevcut Haberler) ve yeni eklenmek istenen aday haberlerin detayları (Yeni Adaylar - Başlık, Özet ve Kategori olarak) verilmiştir.

GÖREV:
Yeni aday haberlerin her birini analiz et. Her aday haber için şu iki kontrolü yap:

1. YAYIN POLİTİKASI UYGUNLUK KONTROLÜ (is_compliant):
   Aday haberin portalımızın yayın politikasına uygun olup olmadığını denetle.
   - Yayın Politikası Odak Alanları: Sadece teknoloji, bilimsel buluşlar, yapay zeka, uzay araştırmaları, kuantum dünyası/bilgisayarları, oyun dünyası (güncellemeler, yeni oyunlar, donanımlar vb.), geek film/dizi duyuruları (bilim kurgu, fantastik, oyun uyarlamaları, sinema teknolojileri) ile ilgili olmalıdır.
   - Politika Dışı (Uygunsuz) Alanlar: Siyaset, politika, genel borsa/yatırım/kripto para (teknolojik altyapısı dışındaki genel finans/fiyat haberleri), standart aşk/dram dizileri veya genel magazin dedikoduları, genel otomotiv incelemeleri (elektrikli/otonom araç teknolojileri dışındaki standart araçlar), yasal uyuşmazlıklar, suç, toplumsal tartışmalar veya polemikler KESİNLİKLE elenmelidir (is_compliant: false).

2. MÜKERRERLİK KONTROLÜ (is_duplicate):
   - Aday haberi sitemizde son 24 saatte yayınlanmış olan "Mevcut Haberler" başlıkları ile karşılaştır. Eğer aday haber, mevcut haberlerden herhangi biriyle semantik (anlamsal) olarak aynı gelişmeyi, lansmanı, duyuruyu veya olayı ele alıyorsa (farklı kelimelerle ifade edilmiş olsa bile semantik olarak aynı gelişme ise), bu haberi mükerrer (is_duplicate: true) olarak işaretle.
   - Aday haberleri kendi aralarında da karşılaştır. Eğer aday haberler arasında semantik olarak aynı konuyu/gelişmeyi ele alan birden fazla haber varsa, sadece bir tanesini onaylayıp (is_duplicate: false), diğerlerini mükerrer (is_duplicate: true) olarak işaretle.

Mevcut Haberler (Son 24 Saat, Sadece Başlıklar):
{existing_titles}

Yeni Adaylar (Ham Adaylar - Başlık, Kategori ve Özet):
{candidates}

Çıktıyı kesinlikle aşağıdaki JSON formatında ver (başka açıklama ekleme):
{
  "results": [
    {
      "id": 1,
      "is_compliant": true,
      "is_duplicate": false,
      "reason": "Gerekçe yazınız (uygun ve özgün veya elenme nedeni)"
    }
  ]
}
"""

    detailed_research_prompt = """Aşağıda kullanıcı tarafından sunulan detaylı araştırma raporunu/metnini incele. Bu metne dayanarak tamamen özgün, Türkçe, akıcı, SEO dostu ve profesyonel bir teknoloji/oyun/sinema/bilim editörü üslubuyla bir haber makalesi yaz.

KRİTİK BİLGİ KAYNAĞI ÖNCELİĞİ KURALI (MANDATORY - %100 UYULMALIDIR):
1. Makaleyi **SADECE VE SADECE** aşağıda verilen araştırma metnindeki bilgilere ve verilere dayanarak yaz.
2. Dışarıdan, internetten veya genel bilgilerden kafana göre **KESİNLİKLE yeni olgular, yeni veriler, hayali olaylar, tarihler veya detaylar ekleme**.
3. Kullanıcının sunduğu araştırma metnindeki tüm teknik detaylara, verilere, tarihlere ve açıklamalara %100 sadık kal.
4. Eğer verilen metinde olmayan bir konu veya detay hakkında haber yapılması isteniyorsa veya metin çok kısıtlıysa, sadece mevcut bilgileri işle, kesinlikle spekülasyon veya hayal ürünü bilgi üretme (Zero Fabrication).

Yazım Tarzı ve Doğruluk Kuralları (MANDATORY):
1. **İlgi Çekici ve Sürükleyici Dil:** Donuk ve makine dili yerine okuyucunun dikkatini ilk cümleden yakalayan, canlı, dinamik ve profesyonel bir üslup kullan.
2. **Konuda Tutucu (Strict Focus):** Haberin odağından kesinlikle sapma. Girdi olarak verilen konunun dışına çıkma, konuyu gereksiz yere dağıtma veya alakasız teknolojilerden bahsetme. Sadece haberin ana konusuna derinlemesine ve tutarlı bir şekilde odaklan.
3. **Clickbait Olmayan Merak Uyandırıcı Başlık:** Clickbait (tık tuzağı veya aldatıcı) olmayan ama merak uyandıran, profesyonel, okuma potansiyeli yüksek Türkçe başlıklar oluştur.
4. **Türkçe Dil ve Çeviri Hassasiyeti:** Araştırma metni veya kaynaklar İngilizce (veya başka bir dilde) ise, haberi anlam kaybı olmadan tamamen Türkçe diline çevirip yaz. Gerekli yerlerde veya teknik terminolojide İngilizce terimleri kullanabilirsin ancak makale tamamen Türkçe olmalıdır.

Hayati Güvenlik ve İçerik Kuralları (MANDATORY):
1. KESİNLİKLE siyaset, politika, devletlerarası krizler, dini konular, toplumsal tartışmalar, yasal ihtilaflar, kişisel karalamalar veya suçlamalar gibi hassas ve yasal risk barındıran konulara girme.
2. Haberlerin odağı sadece saf teknoloji, bilimsel buluşlar, oyun güncellemeleri, yeni dizi/film duyuruları, fragmanlar ve kuantum fiziği/bilgisayarları/teknolojileri olmalıdır.
3. Dizi-Film kategorisi altındaki haberler SADECE bilim kurgu, fantastik, oyun uyarlamaları, dijital yayın teknolojileri (Netflix/Disney+ vb. teknik haberleri) veya sinemada yapay zeka/CGI kullanımıyla ilgili olmalıdır. Yerel/standart aşk dizileri, magazin haberleri, alakasız dram veya genel sinema dedikoduları KESİNLİKLE haber yapılmamalıdır.
4. EĞER GİRDİ HABERİ VEYA ARAŞTIRMA KONUSU BU BELİRTİLEN SINIRLARIN DIŞINDAYSA, kesinlikle makale yazma ve sadece aşağıdaki hata formatında JSON dön:
{
  "error": "Bu konu/haber portalımızın odak alanı (Teknoloji, Oyun, Bilim Kurgu/Geek Dizi-Film, Kuantum) dışındadır."
}
5. Suya sabuna dokunmayan, tamamen tarafsız, objektif, yasal açıdan %100 güvenli, sadece bilgilendirici ve nötr bir dil kullan.
6. Kaynak haberde veya arama sonuçlarında politik veya hukuki bir tartışma/polemik varsa, bu kısımları tamamen temizle ve konuyu yalnızca nesnel teknolojik/endüstriyel boyutuyla ele al.

Genel Yapı & E-E-A-T Katma Değer Kuralları:
1. Haber içeriği en az 4 paragraflık, kapsamlı ve doyurucu bir metin olmalıdır.
2. Metin içinde kesinlikle en az 2 adet analitik alt başlık (markdown ## olarak) kullanılmalıdır. Haber konusuyla en iyi eşleşen iki başlığı seçerek metne entegre et:
   - ## Teknolojik Altyapı ve Yenilikler (Teknik detaylar, mimari, kullanılan yenilikçi yöntemler)
   - ## Sektörel Etki ve Pazar Analizi (Rakiplerle karşılaştırma, endüstri üzerindeki kısa/uzun vadeli etkileri)
   - ## Kullanıcı Deneyimi ve Gelecek Öngörüüsü (Tüketicinin veya oyuncunun elde edeceği fayda, gelecekteki olası gelişmeler)
   - ## Eleştirel Bakış ve Soru İşaretleri (Varsa olumsuz yönler, güvenlik riskleri veya cevaplanmamış sorular)
3. Haberin en sonuna mutlaka "### Editörün Kaleminden" başlığı altında, okuyucuyla bağ kuran, samimi, objektif ve zenginleştirici 2-3 cümlelik derinlemesine bir değerlendirme ekle.
4. Haber için en fazla 160 karakterlik bir SEO meta açıklaması (description) oluştur.
5. Haber kategorisini konuya göre tam olarak şu dördünden biri olarak belirle: "teknoloji", "oyun", "dizi-film" veya "kuantum-evreni". Başka bir kategori adı kesinlikle kullanma.
6. Haberle ilgili 5 adet Türkçe etiket (keywords) belirle.
7. Pexels görsel arama motoru için haberin ana konusunu, markasını ve modelini içeren İngilizce 2-3 kelimelik net ve nokta atışı bir görsel arama sorgusu (pexels_query) yaz. Örnek: "playstation 5 console" (sadece "playstation" yazma), "intel arc gpu" (sadece "gpu" yazma), "quantum computing chip" (sadece "quantum" yazma), "volkswagen ID electric car" (sadece "car" yazma).

Kullanıcının Sunduğu Detaylı Araştırma Metni:
{user_prompt}

Çıktıyı MUTLAKA ```json ``` kod bloğu içinde, geçerli ve temiz bir JSON formatında ver. JSON formatı şu şekilde olmalıdır (Hata durumunda yukarıdaki hata JSON formatını kullanın):
{
  "title": "...",
  "content": "...",
  "description": "...",
  "category": "...",
  "keywords": ["tag1", "tag2", ...],
  "image_prompt": "A detailed 3D concept render of the topic",
  "pexels_query": "..."
}
"""

    search_research_prompt = """Aşağıda kullanıcı tarafından verilen konuyu veya araştırma metnini incele. Bu konuyu Google Search kullanarak detaylıca araştır ve konundan tamamen özgün, Türkçe, akıcı, SEO dostu ve profesyonel bir teknoloji/oyun/sinema/bilim editörü üslubuyla bir haber makalesi yaz.

Yazım Tarzı ve Doğruluk Kuralları (MANDATORY):
1. **İlgi Çekici ve Sürükleyici Dil:** Donuk ve makine dili yerine okuyucunun dikkatini ilk cümleden yakalayan, canlı, dinamik ve profesyonel bir üslup kullan.
2. **Konuda Tutucu (Strict Focus):** Haberin odağından kesinlikle sapma. Girdi olarak verilen konunun dışına çıkma, konuyu gereksiz yere dağıtma veya alakasız teknolojilerden bahsetme. Sadece haberin ana konusuna derinlemesine ve tutarlı bir şekilde odaklan.
3. **KESİNLİKLE YALAN HABER YAPMA (Zero Fabrication):** Asla uydurma veriler, uydurma tarihler, hayali kaynaklar veya yanlış iddialar üretme. Arama sonuçlarındaki gerçek olgulara ve doğrulanabilir verilere %100 sadık kal.
4. **Clickbait Olmayan Merak Uyandırıcı Başlık:** Clickbait (tık tuzağı veya aldatıcı) olmayan ama merak uyandıran, profesyonel, okuma potansiyeli yüksek Türkçe başlıklar oluştur.
5. **Türkçe Dil ve Çeviri Hassasiyeti:** Araştırma kaynakları İngilizce (veya başka bir dilde) ise, haberi anlam kaybı olmadan tamamen Türkçe diline çevirip yaz. Gerekli yerlerde veya teknik terminolojide İngilizce terimleri kullanabilirsin ancak makale tamamen Türkçe olmalıdır.

Hayati Güvenlik ve İçerik Kuralları (MANDATORY):
1. KESİNLİKLE siyaset, politika, devletlerarası krizler, dini konular, toplumsal tartışmalar, yasal ihtilaflar, kişisel karalamalar veya suçlamalar gibi hassas ve yasal risk barındıran konulara girme.
2. Haberlerin odağı sadece saf teknoloji, bilimsel buluşlar, oyun güncellemeleri, yeni dizi/film duyuruları, fragmanlar ve kuantum fiziği/bilgisayarları/teknolojileri olmalıdır.
3. Dizi-Film kategorisi altındaki haberler SADECE bilim kurgu, fantastik, oyun uyarlamaları, dijital yayın teknolojileri (Netflix/Disney+ vb. teknik haberleri) veya sinemada yapay zeka/CGI kullanımıyla ilgili olmalıdır. Yerel/standart aşk dizileri, magazin haberleri, alakasız dram veya genel sinema dedikoduları KESİNLİKLE haber yapılmamalıdır.
4. EĞER GİRDİ HABERİ VEYA ARAŞTIRMA KONUSU BU BELİRTİLEN SINIRLARIN DIŞINDAYSA, kesinlikle makale yazma ve sadece aşağıdaki hata formatında JSON dön:
{
  "error": "Bu konu/haber portalımızın odak alanı (Teknoloji, Oyun, Bilim Kurgu/Geek Dizi-Film, Kuantum) dışındadır."
}
5. Suya sabuna dokunmayan, tamamen tarafsız, objektif, yasal açıdan %100 güvenli, sadece bilgilendirici ve nötr bir dil kullan.
6. Kaynak haberde veya arama sonuçlarında politik veya hukuki bir tartışma/polemik varsa, bu kısımları tamamen temizle ve konuyu yalnızca nesnel teknolojik/endüstriyel boyutuyla ele al.

Genel Yapı & E-E-A-T Katma Değer Kuralları:
1. Haber içeriği en az 4 paragraflık, kapsamlı ve doyurucu bir metin olmalıdır. Ara başlıklar (markdown ## olarak) kullanabilirsin.
2. Metin içinde kesinlikle en az 2 adet analitik alt başlık (markdown ## olarak) kullanılmalıdır. Haber konusuyla en iyi eşleşen iki başlığı seçerek metne entegre et:
   - ## Teknolojik Altyapı ve Yenilikler (Teknik detaylar, mimari, kullanılan yenilikçi yöntemler)
   - ## Sektörel Etki ve Pazar Analizi (Rakiplerle karşılaştırma, endüstri üzerindeki kısa/uzun vadeli etkileri)
   - ## Kullanıcı Deneyimi ve Gelecek Öngörüsü (Tüketicinin veya oyuncunun elde edeceği fayda, gelecekteki olası gelişmeler)
   - ## Eleştirel Bakış ve Soru İşaretleri (Varsa olumsuz yönler, güvenlik riskleri veya cevaplanmamış sorular)
3. Haberin en sonuna mutlaka "### Editörün Kaleminden" başlığı altında, okuyucuyla bağ kuran, samimi, objektif ve zenginleştirici 2-3 cümlelik derinlemesine bir değerlendirme ekle.
4. Haber için en fazla 160 karakterlik bir SEO meta açıklaması (description) oluştur.
5. Haber kategorisini konuya göre tam olarak şu dördünden biri olarak belirle: "teknoloji", "oyun", "dizi-film" veya "kuantum-evreni". Başka bir kategori adı kesinlikle kullanma.
6. Haberle ilgili 5 adet Türkçe etiket (keywords) belirle.
7. Pexels görsel arama motoru için haberin ana konusunu, markasını ve modelini içeren İngilizce 2-3 kelimelik net ve nokta atışı bir görsel arama sorgusu (pexels_query) yaz. Örnek: "playstation 5 console" (sadece "playstation" yazma), "intel arc gpu" (sadece "gpu" yazma), "quantum computing chip" (sadece "quantum" yazma), "volkswagen ID electric car" (sadece "car" yazma).

Araştırılacak Konu / Girdi: {user_prompt}

Çıktıyı MUTLAKA ```json ``` kod bloğu içinde, geçerli ve temiz bir JSON formatında ver. JSON formatı şu şekilde olmalıdır (Hata durumunda yukarıdaki hata JSON formatını kullanın):
{
  "title": "...",
  "content": "...",
  "description": "...",
  "category": "...",
  "keywords": ["tag1", "tag2", ...],
  "image_prompt": "A detailed 3D concept render of the topic",
  "pexels_query": "..."
}
"""

    gemini_prompts_ref = db.collection('system_config').document('gemini_prompts')
    gemini_prompts_ref.set({
        "rewrite_prompt": rewrite_prompt,
        "semantic_duplicates_prompt": semantic_duplicates_prompt,
        "detailed_research_prompt": detailed_research_prompt,
        "search_research_prompt": search_research_prompt
    })
    print("✅ Gemini promptları eklendi.")

    # 3. RSS Kaynakları (Küresel & Yabancı & Telif Muafiyetli/Atıflı)
    rss_sources_ref = db.collection('rss_sources')
    
    # Mevcut tüm kaynakları temizle
    print("Mevcut RSS kaynakları temizleniyor...")
    docs = rss_sources_ref.stream()
    deleted_count = 0
    for doc in docs:
        doc.reference.delete()
        deleted_count += 1
    print(f"✅ Eski RSS kaynakları silindi. (Silinen Döküman: {deleted_count})")
    
    # Yeni küresel telif uyumlu kaynakları ekle
    new_sources = [
        {
            "name": "IGN PC",
            "url": "http://feeds.feedburner.com/ign/pc-articles",
            "category": "oyun"
        },
        {
            "name": "IGN Movies",
            "url": "http://feeds.feedburner.com/ign/movies-articles",
            "category": "dizi-film"
        },
        {
            "name": "ScienceDaily Technology",
            "url": "https://www.sciencedaily.com/rss/matter_energy/technology.xml",
            "category": "teknoloji"
        },
        {
            "name": "Phys.org Technology",
            "url": "https://phys.org/rss-feed/technology-news",
            "category": "teknoloji"
        },
        {
            "name": "arXiv Quantum Physics",
            "url": "https://rss.arxiv.org/rss/quant-ph",
            "category": "kuantum-evreni"
        },
        {
            "name": "ScienceDaily Quantum",
            "url": "https://www.sciencedaily.com/rss/matter_energy/quantum_computing.xml",
            "category": "kuantum-evreni"
        },
        {
            "name": "Phys.org Physics",
            "url": "https://phys.org/rss-feed/physics-news",
            "category": "kuantum-evreni"
        }
    ]
    
    for src in new_sources:
        doc_id = "".join(c for c in src["name"].lower() if c.isalnum() or c == "_")
        rss_sources_ref.document(doc_id).set(src)
        print(f"✅ RSS Kaynağı eklendi: {src['name']}")

    # 4. Otonom Araştırma Ayarları
    research_ref = db.collection('system_config').document('autonomous_research')
    if not research_ref.get().exists:
        research_ref.set({
            "is_active": True,
            "interval_hours": 24,
            "last_run_time": 0.0,
            "is_running": False
        })
        print("✅ Otonom araştırma başlangıç ayarları eklendi.")

    print("🎉 İşlem tamamlandı! Hassas veriler ve küresel RSS kaynakları Firestore üzerinde güncellendi.")

if __name__ == "__main__":
    populate_firestore()
