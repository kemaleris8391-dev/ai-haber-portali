# -*- coding: utf-8 -*-
import os

# Let's construct the code content for populate_firestore_settings.py using unicode escapes for Turkish characters
code = u"""# -*- coding: utf-8 -*-
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

# .env dosyas\u0131ndan gelen Firebase Credentials
load_dotenv(override=True)

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "backend-scripts/firebase_credentials.json"))
        firebase_admin.initialize_app(cred)
    return firestore.client()

def populate_firestore():
    db = initialize_firebase()

    print("Firestore veritaban\u0131 g\u00fcncelleniyor...")

    # 1. Site Ayarlar\u0131
    site_settings_ref = db.collection('system_config').document('site_settings')
    site_settings_ref.set({
        "PUBLIC_BRAND_NAME": "AIHABERLER",
        "PUBLIC_CONTACT_EMAIL": "kemaleris8391@gmail.com",
        "PUBLIC_SITE_URL": "https://aihaberler.web.app"
    })
    print("\u2705 Site ayarlar\u0131 eklendi.")

    # 2. Gemini Promptlar\u0131 (E-E-A-T & Google Discover & AdSense Uyumlu)
    
    rewrite_prompt = \"\"\"A\u015fa\u011f\u0131daki haber ba\u015fl\u0131\u011f\u0131 ve \u00f6zetini analiz et. Bu haberi tamamen \u00f6zg\u00fcn, T\u00fcrk\u00e7e, ak\u0131c\u0131, SEO dostu ve profesyonel bir teknoloji edit\u00f6r\u00fc ve teknik uzman \u00fcslubuyla yeniden yaz. 

Yaz\u0131m Tarz\u0131 ve Do\u011fruluk Kurallar\u0131 (MANDATORY):
1. **\u0130lgi \u00c7ekici ve S\u00fcr\u00fckleyici Dil:** Donuk ve makine dili yerine okuyucunun dikkatini ilk c\u00fcmleden yakalayan, canl\u0131, dinamik ve profesyonel bir \u00fcslup kullan.
2. **Konuda Tutucu (Strict Focus):** Haberin oda\u011f\u0131ndan kesinlikle sapma. Girdi olarak verilen konunun d\u0131\u015f\u0131na \u00e7\u0131kma, konuyu gereksiz yere da\u011f\u0131tma veya alakas\u0131z teknolojilerden bahsetme. Sadece haberin ana konusuna derinlemesine ve tutarl\u0131 bir \u015fekilde odaklan.
3. **KES\u0130NL\u0130KLE YALAN HABER YAPMA (Zero Fabrication):** Asla uydurma veriler, uydurma tarihler, hayali kaynaklar veya yanl\u0131\u015f iddialar \u00fcretme. Girdi haberinde yer alan ger\u00e7ek olgulara ve do\u011frulanabilir verilere %100 sad\u0131k kal.
4. **Clickbait Olmayan Merak Uyand\u0131r\u0131c\u0131 Ba\u015fl\u0131k:** Clickbait (t\u0131k tuza\u011f\u0131 veya aldat\u0131c\u0131) olmayan ama merak uyand\u0131r\u0131c\u0131, profesyonel, okuma potansiyeli y\u00fcksek T\u00fcrk\u00e7e ba\u015fl\u0131klar olu\u015ftur.
5. **T\u00fcrk\u00e7e Dil ve \u00c7eviri Hassasiyeti:** Girdi haber ba\u015fl\u0131\u011f\u0131 veya \u00f6zeti \u0130ngilizce (veya ba\u015fka bir dilde) ise, haberi anlam kayb\u0131 olmadan tamamen T\u00fcrk\u00e7e diline \u00e7evirip yeniden yaz. Gerekli yerlerde veya teknik terminolojide (\u00f6rne\u011fin "CPU", "ray tracing", "pipeline" gibi) \u0130ngilizce terimleri oldu\u011fu gibi kullanabilirsin ancak haberin genel dili ak\u0131c\u0131, anla\u015f\u0131l\u0131r ve tamamen T\u00fcrk\u00e7e olmal\u0131d\u0131r.

Hayati G\u00fcvenlik ve \u0130\u00e7erik Kurallar\u0131 (MANDATORY):
1. KES\u0130NL\u0130KLE siyaset, politika, devletleraras\u0131 krizler, dini konular, toplumsal tart\u0131\u015fmalar, yasal ihtilaflar, ki\u015fisel karalamalar veya su\u00e7lamalar gibi hassas ve yasal risk bar\u0131nd\u0131ran konulara girme.
2. Haberlerin oda\u011f\u0131 sadece PLC programlama ve otomasyonu, PC donan\u0131mlar\u0131 ve bilgisayar teknolojileri, end\u00fcstriyel makineler ve bunlar\u0131n bak\u0131m-tamirleri ile dijital/bilgisayar oyun d\u00fcnyas\u0131 olmal\u0131d\u0131r.
3. Siyaset, politika, magazin, a\u015fk, genel finans/kripto para ve alakas\u0131z konular KES\u0130NL\u0130KLE sisteme al\u0131nmamal\u0131, portal\u0131m\u0131z\u0131n teknoloji, otomasyon ve oyun oda\u011f\u0131 d\u0131\u015f\u0131 ilan edilmelidir.
4. E\u011eER G\u0130RD\u0130 HABER\u0130 BU BEL\u0130RT\u0130LEN SINIRLARIN (PLC, PC, End\u00fcstriyel Makineler, Oyun) DI\u015eINDAYSA, kesinlikle makale yazma ve sadece a\u015fa\u011f\u0131daki hata format\u0131nda JSON d\u00f6n:
{
  "error": "Bu konu/haber portal\u0131m\u0131z\u0131n odak alan\u0131 (PLC, PC, End\u00fcstriyel Makineler, Oyun) d\u0131\u015f\u0131ndad\u0131r."
}
5. Suya sabuna dokunmayan, tamamen tarafs\u0131z, objektif, yasal a\u00e7\u0131dan %100 g\u00fcvenli, sadece bilgilendirici ve n\u00f6tr bir dil kullan.
6. Kaynak haberde politik veya hukuki bir tart\u0131\u015fma/polemik varsa, bu k\u0131s\u0131mlar\u0131 tamamen temizle ve konuyu yaln\u0131zca nesnel teknolojik/end\u00fcstriyel/oyun boyutuyla ele al.

Genel Yap\u0131 & E-E-A-T Katma De\u011fer Kurallar\u0131:
1. Haber i\u00e7eri\u00f0i en az 4 paragrafl\u0131k, kapsaml\u0131 ve doyurucu bir teknik inceleme/makale metni olmal\u0131d\u0131r.
2. Metin i\u00e7inde kesinlikle en az 2 adet analitik alt ba\u015fl\u0131k (markdown ## olarak) kullan\u0131lmal\u0131d\u0131r. Haber konusuyla en iyi e\u015fle\u015fen iki ba\u015fl\u0131\u011f\u0131 se\u00e7erek metne entegre et:
   - ## Teknolojik Altyap\u0131 ve \u00c7al\u0131\u015fma Prensibi (Teknik detaylar, mimari, kullan\u0131lan y\u00f6ntemler)
   - ## Sahadaki Kullan\u0131m ve End\u00fcstriyel/Sekt\u00f6rel Etkileri (Kullan\u0131m alanlar\u0131, verimlilik ve sekt\u00f6rel etkileri)
   - ## Pratik Uygulama ve Sorun Giderme \u00d6ng\u00f6r\u00fcleri (Kar\u015f\u0131la\u015f\u0131labilecek sorunlar ve ar\u0131za \u00e7\u00f6zme \u00f6nerileri)
   - ## Olas\u0131 Riskler ve G\u00fcvenlik \u00d6nlemleri (G\u00fcvenlik \u00f6nlemleri, i\u015f g\u00fcvenli\u011fi ve veri g\u00fcvenli\u011fi hususlar\u0131)
3. Haberin en sonuna mutlaka "### Teknisyenin Sahadan Notu" ba\u015fl\u0131\u011f\u0131 alt\u0131nda, okuyucuyla ba\u011f kuran, samimi, objektif ve zenginle\u015ftirici 2-3 c\u00fcmlelik derinlemesine bir de\u011ferlendirme ekle.
4. "Edit\u00f6r\u00fcn Kaleminden" paragraf\u0131n\u0131n B\u0130T\u0130M\u0130NDE, haberin orijinal kayna\u011f\u0131n\u0131 kesinlikle \u015fu Markdown format\u0131nda ekle: `[Haberin Orijinal Kayna\u011f\u0131: {source_name}]({raw_link})`. Kaynak linki i\u00e7in asla "Link burada", "haberin devam\u0131" gibi ifadeler kullanma.
5. Haber i\u00e7in en fazla 160 karakterlik bir SEO meta a\u00e7\u0131klamas\u0131 (description) olu\u015ftur.
6. Haberle ilgili 5 adet T\u00fcrk\u00e7e etiket (keywords) belirle.
7. Pexels g\u00f6rsel arama motoru i\u00e7in haberin ana konusunu, markas\u0131n\u0131 ve modelini i\u00e7eren \u0130ngilizce 2-3 kelimelik net ve nokta at\u0131\u015f\u0131 bir g\u00f6rsel arama sorgusu (pexels_query) yaz. \u00d6rnek: "playstation 5 console" (sadece "playstation" yazma), "intel arc gpu" (sadece "gpu" yazma), "quantum computing chip" (sadece "quantum" yazma), "volkswagen ID electric car" (sadece "car" yazma).

Girdi Haber Ba\u015fl\u0131\u011f\u0131: {raw_title}
Girdi Haber \u00d6zeti: {raw_summary}
Haber Kategorisi: {category}

\u00c7\u0131kt\u0131y\u0131 a\u015fa\u011f\u0131daki JSON format\u0131nda ver (Hata durumunda yukar\u0131daki hata JSON format\u0131n\u0131 kullan\u0131n):
{
  "title": "...",
  "content": "...",
  "description": "...",
  "keywords": ["tag1", "tag2", ...],
  "image_prompt": "A detailed 3D concept render of the topic",
  "pexels_query": "..."
}
\"\"\"

    semantic_duplicates_prompt = \"\"\"A\u015fa\u011f\u0131da sitemizde son 24 saatte yay\u0131nlanm\u0131\u015f olan haberlerin ba\u015fl\u0131klar\u0131 (Mevcut Haberler) ve yeni eklenmek istenen aday haberlerin detaylar\u0131 (Yeni Adaylar - Ba\u015fl\u0131k, \u00d6zet ve Kategori olarak) verilmi\u015ftir.

G\u00d6REV:
Yeni aday haberlerin her birini analiz et. Her aday haber i\u00e7in \u015fu iki kontrol\u00fc yap:

1. YAY\u0130N POL\u0130T\u0130KASI UYGUNLUK KONTROL\u00dc (is_compliant):
   Aday haberin portal\u0131m\u0131z\u0131n yay\u0131n politikas\u0131na uygun olup olmad\u0131\u011f\u0131n\u0131 denetle.
   - Yay\u0131n Politikas\u0131 Odak Alanlar\u0131: PLC otomasyonu (plc), ki\u015fisel bilgisayarlar ve donan\u0131mlar (pc), end\u00fcstriyel makineler (endustriyel-makinalar), oyun d\u00fcnyas\u0131 (oyun) ile ilgili olmal\u0131d\u0131r.
   - Politika D\u0131\u015f\u0131 (Uygunsuz) Alanlar: Siyaset, politika, genel borsa/yat\u0131r\u0131m/kripto para (teknolojik altyap\u0131s\u0131 d\u0131\u015f\u0131ndaki genel finans/fiyat haberleri), standart a\u015fk/dram dizileri veya genel magazin dedikodular\u0131, genel otomotiv incelemeleri (\u00e5lektrikli/otonom ara\u00e7 teknolojileri d\u0131\u015f\u0131ndaki standart ara\u00e7lar), yasal uyu\u015fmazl\u0131klar, su\u00e7, toplumsal tart\u0131\u015fmalar veya polemikler KES\u0130NL\u0130KLE elenmelidir (is_compliant: false).

2. M\u00dcKERRERL\u0130K KONTROL\u00dc (is_duplicate):
   - Aday haberi sitemizde son 24 saatte yay\u0131nlanm\u0131\u015f olan "Mevcut Haberler" ba\u015fl\u0131klar\u0131 ile kar\u015f\u0131la\u015ft\u0131r. E\u011fer aday haber, mevcut haberlerden herhangi biriyle semantik (anlamsal) olarak ayn\u0131 geli\u015fmeyi, lansman\u0131, duyuruyu veya olay\u0131 ele al\u0131yorsa (farkl\u0131 kelimelerle ifade edilmi\u015f olsa bile semantik olarak ayn\u0131 geli\u015fme ise), bu haberi m\u00fckerrer (is_duplicate: true) olarak i\u015faretle.
   - Aday haberleri kendi aralar\u0131nda da kar\u015f\u0131la\u015ft\u0131r. E\u011fer aday haberler aras\u0131nda semantik olarak ayn\u0131 konuyu/geli\u015fmeyi ele alan birden fazla haber varsa, sadece bir tanesini onaylay\u0131p (is_duplicate: false), di\u011ferlerini m\u00fckerrer (is_duplicate: true) olarak i\u015faretle.

Mevcut Haberler (Son 24 Saat, Sadece Ba\u015fl\u0131klar):
{existing_titles}

Yeni Adaylar (Ham Adaylar - Ba\u015fl\u0131k, Kategori ve \u00d6zet):
{candidates}

\u00c7\u0131kt\u0131y\u0131 kesinlikle a\u015fa\u011f\u0131daki JSON format\u0131nda ver (ba\u015fka a\u00e7\u0131klama ekleme):
{
  "results": [
    {
      "id": 1,
      "is_compliant": true,
      "is_duplicate": false,
      "reason": "Gerek\u00e7e yaz\u0131n\u0131z (uygun ve \u00f6zg\u00fcn veya elenme nedeni)"
    }
  ]
}
\"\"\"

    detailed_research_prompt = \"\"\"A\u015fa\u011f\u0131da kullan\u0131c\u0131 taraf\u0131ndan sunulan detayl\u0131 ara\u015ft\u0131rma raporunu/metnini incele. Bu metne dayanarak tamamen \u00f6zg\u00fcn, T\u00fcrk\u00e7e, ak\u0131c\u0131, SEO dostu ve profesyonel bir teknoloji edit\u00f6r\u00fc ve teknik uzman \u00fcslubuyla bir haber makalesi yaz.

KR\u0130T\u0130K B\u0130LG\u0130 KAYNA\u011eI \u00d6NCEL\u0130\u011e\u0130 KURALI (MANDATORY - %100 UYULMALIDIR):
1. Makaleyi **SADECE VE SADECE** a\u015fa\u011f\u0131da verilen ara\u015ft\u0131rma metnindeki bilgilere ve verilere dayanarak yaz.
2. D\u0131\u015far\u0131dan, internetten veya genel bilgilerden kafana g\u00f6re **KES\u0130NL\u0130KLE yeni olgular, yeni veriler, hayali olaylar, tarihler veya detaylar ekleme**.
3. Kullan\u0131c\u0131n\u0131n sundu\u011fu ara\u015ft\u0131rma metnindeki t\u00fcm teknik detaylara, verilere, tarihlere ve a\u00e7\u0131klamalara %100 sad\u0131k kal.
4. E\u011fer verilen metinde olmayan bir konu veya detay hakk\u0131nda haber yap\u0131lmas\u0131 isteniyorsa veya metin \u00e7ok k\u0131s\u0131tl\u0131ysa, sadece mevcut bilgileri i\u015fle, kesinlikle spek\u00fclasyon veya hayal \u00fcr\u00fcn\u00fc bilgi \u00fcretme (Zero Fabrication).

Yaz\u0131m Tarz\u0131 ve Do\u011fruluk Kurallar\u0131 (MANDATORY):
1. **\u0130lgi \u00c7ekici ve S\u00fcr\u00fckleyici Dil:** Donuk ve makine dili yerine okuyucunun dikkatini ilk c\u00fcmleden yakalayan, canl\u0131, dinamik ve profesyonel bir \u00fcslup kullan.
2. **Konuda Tutucu (Strict Focus):** Haberin oda\u011f\u0131ndan kesinlikle sapma. Girdi olarak verilen konunun d\u0131\u015f\u0131na \u00e7\u0131kma, konuyu gereksiz yere da\u011f\u0131tma veya alakas\u0131z teknolojilerden bahsetme. Sadece haberin ana konusuna derinlemesine ve tutarl\u0131 bir \u015fekilde odaklan.
3. **Clickbait Olmayan Merak Uyand\u0131r\u0131c\u0131 Ba\u015fl\u0131k:** Clickbait (t\u0131k tuza\u011f\u0131 veya aldat\u0131c\u0131) olmayan ama merak uyand\u0131r\u0131c\u0131, profesyonel, okuma potansiyeli y\u00fcksek T\u00fcrk\u00e7e ba\u015fl\u0131klar olu\u015ftur.
4. **T\u00fcrk\u00e7e Dil ve \u00c7eviri Hassasiyeti:** Ara\u015ft\u0131rma metni veya kaynaklar \u0130ngilizce (veya ba\u015fka bir dilde) ise, haberi anlam kayb\u0131 olmadan tamamen T\u00fcrk\u00e7e diline \u00e7evirip yaz. Gerekli yerlerde veya teknik terminolojide \u0130ngilizce terimleri kullanabilirsin ancak makale tamamen T\u00fcrk\u00e7e olmal\u0131d\u0131r.

Hayati G\u00fcvenlik ve \u0130\u00e7erik Kurallar\u0131 (MANDATORY):
1. KES\u0130NL\u0130KLE siyaset, politika, devletlerarası krizler, dini konular, toplumsal tart\u0131\u015fmalar, yasal ihtilaflar, ki\u015fisel karalamalar veya su\u00e7lamalar gibi hassas ve yasal risk bar\u0131nd\u0131ran konulara girme.
2. Haberlerin oda\u011f\u0131 sadece PLC programlama ve otomasyonu, PC donan\u0131mlar\u0131 ve bilgisayar teknolojileri, end\u00fcstriyel makineler ve bunlar\u0131n bak\u0131m-tamirleri ile dijital/bilgisayar oyun d\u00fcnyas\u0131 olmal\u0131d\u0131r.
3. Siyaset, politika, magazin, a\u015fk, genel finans/kripto para ve alakas\u0131z konular KES\u0130NL\u0130KLE sisteme al\u0131nmamal\u0131d\u0131r.
4. E\u011eER G\u0130RD\u0130 HABER\u0130 VEYA ARA\u015eTIRMA KONUSU BU BEL\u0130RT\u0100LEN SINIRLARIN DI\u015eINDAYSA, kesinlikle makale yazma ve sadece a\u015fa\u011f\u0131daki hata format\u0131nda JSON d\u00f6n:
{
  "error": "Bu konu/haber portal\u0131m\u0131z\u0131n odak alan\u0131 (PLC, PC, End\u00fcstriyel Makineler, Oyun) d\u0131\u015f\u0131ndad\u0131r."
}
5. Suya sabuna dokunmayan, tamamen tarafs\u0131z, objektif, yasal a\u00e7\u0131dan %100 g\u00fcvenli, sadece bilgilendirici ve n\u00f6tr bir dil kullan.
6. Kaynak haberde veya arama sonu\u00e7lar\u0131nda politik veya hukuki bir tart\u0131\u015fma/polemik varsa, bu k\u0131s\u0131mlar\u0131 tamamen temizle ve konuyu yaln\u0131zca nesnel teknolojik/end\u00fcstriyel/oyun boyutuyla ele al.

Genel Yap\u0131 & E-E-A-T Katma De\u011fer Kurallar\u0131:
1. Haber i\u00e7eri\u00f0i en az 4 paragrafl\u0131k, kapsam\u0131d\u0131 ve doyurucu bir metin olmal\u0131d\u0131r.
2. Metin i\u00e7inde kesinlikle en az 2 adet analitik alt ba\u015fl\u0131k (markdown ## olarak) kullan\u0131lmal\u0131d\u0131r. Haber konusuyla en iyi e\u015fle\u015fen iki ba\u015fl\u0131\u011f\u0131 se\u00e7erek metne entegre et:
   - ## Teknolojik Altyap\u0131 ve \u00c7al\u0131\u015fma Prensibi (Teknik detaylar, mimari, kullan\u0131lan y\u00f6ntemler)
   - ## Sahadaki Kullan\u0131m ve End\u00fcstriyel/Sekt\u00f6rel Etkileri (Kullan\u0131m alanlar\u0131, verimlilik ve sekt\u00f6rel etkileri)
   - ## Pratik Uygulama ve Sorun Giderme \u00d6ng\u00f6r\u00fcleri (Kar\u015f\u0131la\u015f\u0131labilecek sorunlar ve ar\u0131za \u00e7\u00f6zme \u00f6nerileri)
   - ## Olas\u0131 Riskler ve G\u00fcvenlik \u00d6nlemleri (G\u00fcvenlik \u00f6nlemleri, i\u015f g\u00fcvenli\u011fi ve veri g\u00fcvenli\u011fi hususlar\u0131)
3. Haberin en sonuna mutlaka "### Teknisyenin Sahadan Notu" ba\u015fl\u0131\u011f\u0131 alt\u0131nda, okuyucuyla ba\u011f kuran, samimi, objektif ve zenginle\u015ftirici 2-3 c\u00fcmlelik derinlemesine bir de\u011ferlendirme ekle.
4. Haber i\u00e7in en fazla 160 karakterlik bir SEO meta a\u00e7\u0131klamas\u0131 (description) olu\u015ftur.
5. Haber kategorisini konuya g\u00f6re tam olarak \u015fu d\u00f6rd\u00fcnden biri olarak belirle: "plc", "pc", "endustriyel-makinalar" veya "oyun". Ba\u015fka bir kategori ad\u0131 kesinlikle kullanma.
6. Haberle ilgili 5 adet T\u00fcrk\u00e7e etiket (keywords) belirle.
7. Pexels g\u00f6rsel arama motoru i\u00e7in haberin ana konusunu, markas\u0131n\u0131 ve modelini i\u00e7eren \u0130ngilizce 2-3 kelimelik net ve nokta at\u0131\u015f\u0131 bir g\u00f6rsel arama sorgusu (pexels_query) yaz. \u00d6rnek: "playstation 5 console" (sadece "playstation" yazma), "intel arc gpu" (sadece "gpu" yazma), "quantum computing chip" (sadece "quantum" yazma), "volkswagen ID electric car" (sadece "car" yazma).

Kullan\u0131c\u0131n\u0131n Sundu\u011fu Detayl\u0131 Ara\u015ft\u0131rma Metni:
{user_prompt}

\u00c7\u0131kt\u0131y\u0131 MUTLAKA ```json ``` kod blo\u011fu i\u00e7inde, ge\u00e7erli ve temiz bir JSON format\u0131nda ver. JSON format\u0131 \u015fu \u015fekilde olmal\u0131d\u0131r (Hata durumunda yukar\u0131daki hata JSON format\u0131n\u0131 kullan\u0131n):
{
  "title": "...",
  "content": "...",
  "description": "...",
  "category": "...",
  "keywords": ["tag1", "tag2", ...],
  "image_prompt": "A detailed 3D concept render of the topic",
  "pexels_query": "..."
}
\"\"\"

    search_research_prompt = \"\"\"A\u015fa\u011f\u0131da kullan\u0131c\u0131 taraf\u0131ndan verilen konuyu veya ara\u015ft\u0131rma metnini incele. Bu konuyu Google Search kullanarak detayl\u0131ca ara\u015ft\u0131r ve konundan tamamen \u00f6zg\u00fcn, T\u00fcrk\u00e7e, ak\u0131c\u0131, SEO dostu ve profesyonel bir teknoloji edit\u00f6r\u00fc ve teknik uzman \u00fcslubuyla bir haber makalesi yaz.

Yaz\u0131m Tarz\u0131 ve Do\u011fruluk Kurallar\u0131 (MANDATORY):
1. **\u0130lgi \u00c7ekici ve S\u00fcr\u00fckleyici Dil:** Donuk ve makine dili yerine okuyucunun dikkatini ilk c\u00fcmleden yakalayan, canl\u0131, dinamik ve profesyonel bir \u00fcslup kullan.
2. **Konuda Tutucu (Strict Focus):** Haberin oda\u011f\u0131ndan kesinlikle sapma. Girdi olarak verilen konunun d\u0131\u015f\u0131na \u00e7\u0131kma, konuyu gereksiz yere da\u011f\u0131tma veya alakas\u0131z teknolojilerden bahsetme. Sadece haberin ana konusuna derinlemesine ve tutarl\u0131 bir \u015fekilde odaklan.
3. **KES\u0130NL\u0130KLE YALAN HABER YAPMA (Zero Fabrication):** Asla uydurma veriler, uydurma tarihler, hayali kaynaklar veya yanl\u0131\u015f iddialar \u00fcretme. Arama sonu\u00e7lar\u0131ndaki ger\u00e7ek olgulara ve do\u011frulanabilir verilere %100 sad\u0131k kal.
4. **Clickbait Olmayan Merak Uyand\u0131r\u0131c\u0131 Ba\u015fl\u0131k:** Clickbait (t\u0131k tuza\u011f\u0131 veya aldat\u0131c\u0131) olmayan ama merak uyand\u0131r\u0131c\u0131, profesyonel, okuma potansiyeli y\u00fcksek T\u00fcrk\u00e7e ba\u015fl\u0131klar olu\u015ftur.
5. **T\u00fcrk\u00e7e Dil ve \u00c7eviri Hassasiyeti:** Ara\u015ft\u0131rma kaynaklar\u0131 \u0130ngilizce (veya ba\u015fka bir dilde) ise, haberi anlam kayb\u0131 olmadan tamamen T\u00fcrk\u00e7e diline \u00e7evirip yaz. Gerekli yerlerde veya teknik terminolojide \u0130ngilizce terimleri kullanabilirsin ancak makale tamamen T\u00fcrk\u00e7e olmal\u0131d\u0131r.

Hayati G\u00fcvenlik ve \u0130\u00e7erik Kurallar\u0131 (MANDATORY):
1. KES\u0130NL\u0130KLE siyaset, politika, devletlerarası krizler, dini konular, toplumsal tart\u0131\u015fmalar, yasal ihtilaflar, ki\u015fisel karalamalar veya su\u00e7lamalar gibi hassas ve yasal risk bar\u0131nd\u0131ran konulara girme.
2. Haberlerin oda\u011f\u0131 sadece PLC programlama ve otomasyonu, PC donan\u0131mlar\u0131 ve bilgisayar teknolojileri, end\u00fcstriyel makineler ve bunlar\u0131n bak\u0131m-tamirleri ile dijital/bilgisayar oyun d\u00fcnyas\u0131 olmal\u0131d\u0131r.
3. Siyaset, politika, magazin, a\u015fk, genel finans/kripto para ve alakas\u0131z konular KES\u0130NL\u0130KLE sisteme al\u0131nmamal\u0131d\u0131r.
4. E\u011eER G\u0130RD\u0130 HABER\u0130 VEYA ARA\u015eTIRMA KONUSU BU BEL\u0130RT\u0100LEN SINIRLARIN DI\u015eINDAYSA, kesinlikle makale yazma ve sadece a\u015fa\u011f\u0131daki hata format\u0131nda JSON d\u00f6n:
{
  "error": "Bu konu/haber portal\u0131m\u0131z\u0131n odak alan\u0131 (PLC, PC, End\u00fcstriyel Makineler, Oyun) d\u0131\u015f\u0131ndad\u0131r."
}
5. Suya sabuna dokunmayan, tamamen tarafs\u0131z, objektif, yasal a\u00e7\u0131dan %100 g\u00fcvenli, sadece bilgilendirici ve n\u00f6tr bir dil kullan.
6. Kaynak haberde veya arama sonu\u00e7lar\u0131nda politik veya hukuki bir tart\u0131\u015fma/polemik varsa, bu k\u0131s\u0131mlar\u0131 tamamen temizle ve konuyu yaln\u0131zca nesnel teknolojik/end\u00fcstriyel/oyun boyutuyla ele al.

Genel Yap\u0131 & E-E-A-T Katma De\u011fer Kurallar\u0131:
1. Haber i\u00e7eri\u00f0i en az 4 paragrafl\u0131k, kapsaml\u0131 ve doyurucu bir metin olmal\u0131d\u0131r. Ara ba\u015fl\u0131klar (markdown ## olarak) kullanabilirsin.
2. Metin i\u00e7inde kesinlikle en az 2 adet analitik alt ba\u015fl\u0131k (markdown ## olarak) kullan\u0131lmal\u0131d\u0131r. Haber konusuyla en iyi e\u015fle\u015fen iki ba\u015fl\u0131\u011f\u0131 se\u00e7erek metne entegre et:
   - ## Teknolojik Altyap\u0131 ve \u00c7al\u0131\u015fma Prensibi (Teknik detaylar, mimari, kullan\u0131lan y\u00f6ntemler)
   - ## Sahadaki Kullan\u0131m ve End\u00fcstriyel/Sekt\u00f6rel Etkileri (Kullan\u0131m alanlar\u0131, verimlilik ve sekt\u00f6rel etkileri)
   - ## Pratik Uygulama ve Sorun Giderme \u00d6ng\u00f6r\u00fcleri (Kar\u015f\u0131la\u015f\u0131labilecek sorunlar ve ar\u0131za \u00e7\u00f6zme \u00f6nerileri)
   - ## Olas\u0131 Riskler ve G\u00fcvenlik \u00d6nlemleri (G\u00fcvenlik \u00f6nlemleri, i\u015f g\u00fcvenli\u011fi ve veri g\u00fcvenli\u011fi hususlar\u0131)
3. Haberin en sonuna mutlaka "### Teknisyenin Sahadan Notu" ba\u015fl\u0131\u011f\u0131 alt\u0131nda, okuyucuyla ba\u011f kuran, samimi, objektif ve zenginle\u015ftirici 2-3 c\u00fcmlelik derinlemesine bir de\u011ferlendirme ekle.
4. Haber i\u00e7in en fazla 160 karakterlik bir SEO meta a\u00e7\u0131klamas\u0131 (description) olu\u015ftur.
5. Haber kategorisini konuya g\u00f6re tam olarak \u015fu d\u00f6rd\u00fcnden biri olarak belirle: "plc", "pc", "endustriyel-makinalar" veya "oyun". Ba\u015fka bir kategori ad\u0131 kesinlikle kullanma.
6. Haberle ilgili 5 adet T\u00fcrk\u00e7e etiket (keywords) belirle.
7. Pexels g\u00f6rsel arama motoru i\u00e7in haberin ana konusunu, markas\u0131n\u0131 ve modelini i\u00e7eren \u0130ngilizce 2-3 kelimelik net ve nokta at\u0131\u015f\u0131 bir g\u00f6rsel arama sorgusu (pexels_query) yaz. \u00d6rnek: "playstation 5 console" (sadece "playstation" yazma), "intel arc gpu" (sadece "gpu" yazma), "quantum computing chip" (sadece "quantum" yazma), "volkswagen ID electric car" (sadece "car" yazma).

Ara\u015ft\u0131r\u0131lacak Konu / Girdi: {user_prompt}

\u00c7\u0131kt\u0131y\u0131 MUTLAKA ```json ``` kod blo\u011fu i\u00e7inde, ge\u00e7erli ve temiz bir JSON format\u0131nda ver. JSON format\u0131 \u015fu \u015fekilde olmal\u0131d\u0131r (Hata durumunda yukar\u0131daki hata JSON format\u0131n\u0131 kullan\u0131n):
{
  "title": "...",
  "content": "...",
  "description": "...",
  "category": "...",
  "keywords": ["tag1", "tag2", ...],
  "image_prompt": "A detailed 3D concept render of the topic",
  "pexels_query": "..."
}
\"\"\"

    gemini_prompts_ref = db.collection('system_config').document('gemini_prompts')
    gemini_prompts_ref.set({
        "rewrite_prompt": rewrite_prompt,
        "semantic_duplicates_prompt": semantic_duplicates_prompt,
        "detailed_research_prompt": detailed_research_prompt,
        "search_research_prompt": search_research_prompt
    })
    print("\u2705 Gemini promptlar\u0131 eklendi.")

    # 3. RSS Kaynaklar\u0131 (K\u00fcresel & Yabanc\u0131 & Telif Muafiyetli/At\u0131fl\u0131)
    rss_sources_ref = db.collection('rss_sources')
    
    # Mevcut t\u00fcm kaynaklar\u0131 temizle
    print("Mevcut RSS kaynaklar\u0131 temizleniyor...")
    docs = rss_sources_ref.stream()
    deleted_count = 0
    for doc in docs:
        doc.reference.delete()
        deleted_count += 1
    print(f"\u2705 Eski RSS kaynaklar\u0131 silindi. (Silinen D\u00f6k\u00fcman: {deleted_count})")
    
    # Yeni k\u00fcresel telif uyumlu kaynaklar\u0131 ekle
    new_sources = [
        {
            "name": "Control.com",
            "url": "https://control.com/rss",
            "category": "plc"
        },
        {
            "name": "Automation World",
            "url": "https://www.automationworld.com/rss",
            "category": "endustriyel-makinalar"
        },
        {
            "name": "iFixit News",
            "url": "https://www.ifixit.com/News/rss",
            "category": "pc"
        },
        {
            "name": "Hackaday",
            "url": "https://hackaday.com/blog/feed/",
            "category": "pc"
        },
        {
            "name": "ScienceDaily Tech",
            "url": "https://www.sciencedaily.com/rss/matter_energy/technology.xml",
            "category": "pc"
        },
        {
            "name": "Phys.org Tech",
            "url": "https://phys.org/rss-feed/technology-news",
            "category": "pc"
        },
        {
            "name": "IGN Games",
            "url": "https://feeds.feedburner.com/ign/news",
            "category": "oyun"
        }
    ]
    
    for src in new_sources:
        doc_id = "".join(c for c in src["name"].lower() if c.isalnum() or c == "_")
        rss_sources_ref.document(doc_id).set(src)
        print(f"\u2705 RSS Kayna\u011f\u0131 eklendi: {src['name']}")

    # 4. Otonom Ara\u015ft\u0131rma Ayarlar\u0131
    research_ref = db.collection('system_config').document('autonomous_research')
    research_ref.set({
        "is_active": True,
        "interval_hours": 24,
        "last_run_time": 0.0,
        "is_running": False,
        "inspiration_hours": 24,
        "max_topics": 2
    }, merge=True)
    print("\u2705 Otonom ara\u015ft\u0131rma ba\u015flang\u0131\u00e7 ayarlar\u0131 eklendi.")

    # 5. Default Categories
    categories_ref = db.collection('system_config').document('categories')
    categories_ref.set({
        "list": ["plc", "pc", "endustriyel-makinalar", "oyun"]
    })
    print("\u2705 Varsay\u0131lan kategoriler listesi Firestore'a eklendi.")

    print("\u1f389 \u0130\u015flem tamamland\u0131! Hassas veriler ve k\u00fcresel RSS kaynaklar\u0131 Firestore \u00fczerinde g\u00fcncellendi.")

if __name__ == "__main__":
    populate_firestore()
"""

with open(r"backend-scripts/populate_firestore_settings.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully updated backend-scripts/populate_firestore_settings.py")
