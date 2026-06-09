import json

path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\backend-scripts\prompts_config.json"

with open(path, "r", encoding="utf-8") as f:
    config = json.load(f)

# 1. Update rewrite_prompt
rewrite = config["rewrite_prompt"]
rewrite = rewrite.replace(
    "teknoloji/oyun/sinema editörü",
    "elektronik teknisyeni ve endüstriyel otomasyon uzmanı"
)
rewrite = rewrite.replace(
    'saf teknoloji, bilimsel buluşlar, oyun güncellemeleri, yeni dizi/film duyuruları, fragmanlar ve kuantum fiziği/bilgisayarları/teknolojileri',
    'endüstriyel otomasyon, PLC yazılımları, servo/step motorlar, sensörler, makine tamiri ve elektrik-elektronik donanım arıza çözümleri'
)
rewrite = rewrite.replace(
    'Dizi-Film kategorisi altındaki haberler SADECE bilim kurgu, fantastik, oyun uyarlamaları, dijital yayın teknolojileri (Netflix/Disney+ vb. teknik haberleri) veya sinemada yapay zeka/CGI kullanımıyla ilgili olmalıdır. Yerel/standart aşk dizileri, magazin haberleri, alakasız dram veya genel sinema dedikoduları KESİNLİKLE haber yapılmamalıdır.',
    'Dizi, sinema, magazin, aşk, siyaset, spor, genel finans ve alakasız oyun haberleri KESİNLİKLE sisteme alınmamalı, portalımızın teknik teknisyen odağı dışı ilan edilmelidir.'
)
rewrite = rewrite.replace(
    'Bu konu/haber portalımızın odak alanı (Teknoloji, Oyun, Bilim Kurgu/Geek Dizi-Film, Kuantum) dışındadır.',
    'Bu konu/haber portalımızın odak alanı (Otomasyon & PLC, Endüstriyel Tamir & Bakım, Donanım & Pratik Çözümler) dışındadır.'
)
rewrite = rewrite.replace(
    'Teknoloji, Oyun, Bilim Kurgu/Geek Dizi-Film, Kuantum',
    'Otomasyon & PLC, Endüstriyel Tamir & Bakım, Donanım & Pratik Çözümler'
)
rewrite = rewrite.replace(
    '## Teknolojik Altyapı ve Yenilikler (Teknik detaylar, mimari, kullanılan yenilikçi yöntemler)',
    '## Teknolojik Altyapı ve Çalışma Prensibi (Teknik detaylar, mimari, kullanılan yöntemler)'
)
rewrite = rewrite.replace(
    '## Sektörel Etki ve Pazar Analizi (Rakiplerle karşılaştırma, endüstri üzerindeki kısa/uzun vadeli etkileri)',
    '## Sahadaki Kullanım ve Endüstriyel Etkileri (Kullanım alanları, verimlilik ve endüstriyel etkileri)'
)
rewrite = rewrite.replace(
    '## Kullanıcı Deneyimi ve Gelecek Öngörüsü (Tüketicinin veya oyuncunun elde edeceği fayda, gelecekteki olası gelişmeler)',
    '## Pratik Uygulama ve Sorun Giderme Öngörüleri (Karşılaşılabilecek sorunlar ve arıza çözme önerileri)'
)
rewrite = rewrite.replace(
    '## Eleştirel Bakış ve Soru İşaretleri (Varsa olumsuz yönler, güvenlik riskleri veya cevaplanmamış sorular)',
    '## Olası Riskler ve Güvenlik Önlemleri (Elektriksel/mekanik güvenlik önlemleri, iş güvenliği hususları)'
)
rewrite = rewrite.replace(
    '\"teknoloji\", \"oyun\", \"dizi-film\" veya \"kuantum-evreni\"',
    '\"otomasyon-plc\", \"endustriyel-tamir\" veya \"donanim-pratik\"'
)
rewrite = rewrite.replace(
    '\"teknoloji\", \"oyun\", \"dizi-film\" ve \"kuantum-evreni\"',
    '\"otomasyon-plc\", \"endustriyel-tamir\" ve \"donanim-pratik\"'
)
rewrite = rewrite.replace(
    '### Editörün Kaleminden',
    '### Teknisyenin Sahadan Notu'
)
config["rewrite_prompt"] = rewrite

# 2. Update semantic_duplicates_prompt
duplicates = config["semantic_duplicates_prompt"]
duplicates = duplicates.replace(
    'Sadece teknoloji, bilimsel buluşlar, yapay zeka, uzay araştırmaları, kuantum dünyası/bilgisayarları, oyun dünyası (güncellemeler, yeni oyunlar, donanımlar vb.), geek film/dizi duyuruları (bilim kurgu, fantastik, oyun uyarlamaları, sinema teknolojileri) ile ilgili olmalıdır.',
    'Sadece otomasyon-plc (PLC programlama, servo/step motorlar, HMI, sensörler), endustriyel-tamir (fabrika arıza giderme, makine bakımı, pano tasarımı, elektrik devreleri) ve donanim-pratik (ev elektroniği, PC donanımı, telefon tamirleri, pratik elektrik arızaları) ile ilgili olmalıdır.'
)
duplicates = duplicates.replace(
    'siyaset, genel borsa/yatırım/kripto para (teknolojik altyapısı dışındaki genel finans/fiyat haberleri), standart aşk/dram dizileri veya genel magazin dedikoduları, genel otomotiv incelemeleri (elektrikli/otonom araç teknolojileri dışındaki standart araçlar), yasal uyuşmazlıklar, suç, toplumsal tartışmalar veya polemikler KESİNLİKLE elenmelidir',
    'siyaset, magazin, dizi, sinema, genel borsa, kripto para, genel otomotiv, suç, genel spor haberleri KESİNLİKLE elenmelidir'
)
config["semantic_duplicates_prompt"] = duplicates

# 3. Update detailed_research_prompt
detailed = config["detailed_research_prompt"]
detailed = detailed.replace(
    "teknoloji/oyun/sinema/bilim editörü",
    "elektronik teknisyeni ve endüstriyel otomasyon uzmanı"
)
detailed = detailed.replace(
    'saf teknoloji, bilimsel buluşlar, oyun güncellemeleri, yeni dizi/film duyuruları, fragmanlar ve kuantum fiziği/bilgisayarları/teknolojileri',
    'endüstriyel otomasyon, PLC yazılımları, servo/step motorlar, sensörler, makine tamiri ve elektrik-elektronik donanım arıza çözümleri'
)
detailed = detailed.replace(
    'Dizi-Film kategorisi altındaki haberler SADECE bilim kurgu, fantastik, oyun uyarlamaları, dijital yayın teknolojileri (Netflix/Disney+ vb. teknik haberleri) veya sinemada yapay zeka/CGI kullanımıyla ilgili olmalıdır. Yerel/standart aşk dizileri, magazin haberleri, alakasız dram veya genel sinema dedikoduları KESİNLİKLE haber yapılmamalıdır.',
    'Dizi, sinema, magazin, aşk, siyaset, spor, genel finans ve alakasız oyun haberleri KESİNLİKLE sisteme alınmamalıdır.'
)
detailed = detailed.replace(
    'Bu konu/haber portalımızın odak alanı (Teknoloji, Oyun, Bilim Kurgu/Geek Dizi-Film, Kuantum) dışındadır.',
    'Bu konu/haber portalımızın odak alanı (Otomasyon & PLC, Endüstriyel Tamir & Bakım, Donanım & Pratik Çözümler) dışındadır.'
)
detailed = detailed.replace(
    '## Teknolojik Altyapı ve Yenilikler (Teknik detaylar, mimari, kullanılan yenilikçi yöntemler)',
    '## Teknolojik Altyapı ve Çalışma Prensibi (Teknik detaylar, mimari, kullanılan yöntemler)'
)
detailed = detailed.replace(
    '## Sektörel Etki ve Pazar Analizi (Rakiplerle karşılaştırma, endüstri üzerindeki kısa/uzun vadeli etkileri)',
    '## Sahadaki Kullanım ve Endüstriyel Etkileri (Kullanım alanları, verimlilik ve endüstriyel etkileri)'
)
detailed = detailed.replace(
    '## Kullanıcı Deneyimi ve Gelecek Öngörüüsü (Tüketicinin veya oyuncunun elde edeceği fayda, gelecekteki olası gelişmeler)',
    '## Pratik Uygulama ve Sorun Giderme Öngörüleri (Karşılaşılabilecek sorunlar ve arıza çözme önerileri)'
)
detailed = detailed.replace(
    '## Eleştirel Bakış ve Soru İşaretleri (Varsa olumsuz yönler, güvenlik riskleri veya cevaplanmamış sorular)',
    '## Olası Riskler ve Güvenlik Önlemleri (Elektriksel/mekanik güvenlik önlemleri, iş güvenliği hususları)'
)
detailed = detailed.replace(
    '\"teknoloji\", \"oyun\", \"dizi-film\" veya \"kuantum-evreni\"',
    '\"otomasyon-plc\", \"endustriyel-tamir\" veya \"donanim-pratik\"'
)
detailed = detailed.replace(
    '### Editörün Kaleminden',
    '### Teknisyenin Sahadan Notu'
)
config["detailed_research_prompt"] = detailed

# 4. Update search_research_prompt
search_p = config["search_research_prompt"]
search_p = search_p.replace(
    "teknoloji/oyun/sinema/bilim editörü",
    "elektronik teknisyeni ve endüstriyel otomasyon uzmanı"
)
search_p = search_p.replace(
    'saf teknoloji, bilimsel buluşlar, oyun güncellemeleri, yeni dizi/film duyuruları, fragmanlar ve kuantum fiziği/bilgisayarları/teknolojileri',
    'endüstriyel otomasyon, PLC yazılımları, servo/step motorlar, sensörler, makine tamiri ve elektrik-elektronik donanım arıza çözümleri'
)
search_p = search_p.replace(
    'Dizi-Film kategorisi altındaki haberler SADECE bilim kurgu, fantastik, oyun uyarlamaları, dijital yayın teknolojileri (Netflix/Disney+ vb. teknik haberleri) veya sinemada yapay zeka/CGI kullanımıyla ilgili olmalıdır. Yerel/standart aşk dizileri, magazin haberleri, alakasız dram veya genel sinema dedikoduları KESİNLİKLE haber yapılmamalıdır.',
    'Dizi, sinema, magazin, aşk, siyaset, spor, genel finans ve alakasız oyun haberleri KESİNLİKLE sisteme alınmamalıdır.'
)
search_p = search_p.replace(
    'Bu konu/haber portalımızın odak alanı (Teknoloji, Oyun, Bilim Kurgu/Geek Dizi-Film, Kuantum) dışındadır.',
    'Bu konu/haber portalımızın odak alanı (Otomasyon & PLC, Endüstriyel Tamir & Bakım, Donanım & Pratik Çözümler) dışındadır.'
)
search_p = search_p.replace(
    '## Teknolojik Altyapı ve Yenilikler (Teknik detaylar, mimari, kullanılan yenilikçi yöntemler)',
    '## Teknolojik Altyapı ve Çalışma Prensibi (Teknik detaylar, mimari, kullanılan yöntemler)'
)
search_p = search_p.replace(
    '## Sektörel Etki ve Pazar Analizi (Rakiplerle karşılaştırma, endüstri üzerindeki kısa/uzun vadeli etkileri)',
    '## Sahadaki Kullanım ve Endüstriyel Etkileri (Kullanım alanları, verimlilik ve endüstriyel etkileri)'
)
search_p = search_p.replace(
    '## Kullanıcı Deneyimi ve Gelecek Öngörüsü (Tüketicinin veya oyuncunun elde edeceği fayda, gelecekteki olası gelişmeler)',
    '## Pratik Uygulama ve Sorun Giderme Öngörüleri (Karşılaşılabilecek sorunlar ve arıza çözme önerileri)'
)
search_p = search_p.replace(
    '## Eleştirel Bakış ve Soru İşaretleri (Varsa olumsuz yönler, güvenlik riskleri veya cevaplanmamış sorular)',
    '## Olası Riskler ve Güvenlik Önlemleri (Elektriksel/mekanik güvenlik önlemleri, iş güvenliği hususları)'
)
search_p = search_p.replace(
    '\"teknoloji\", \"oyun\", \"dizi-film\" veya \"kuantum-evreni\"',
    '\"otomasyon-plc\", \"endustriyel-tamir\" veya \"donanim-pratik\"'
)
search_p = search_p.replace(
    '### Editörün Kaleminden',
    '### Teknisyenin Sahadan Notu'
)
config["search_research_prompt"] = search_p

# Write back
with open(path, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=4)

print("Prompts successfully updated!")
