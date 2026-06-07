import os
import re

blog_dir = 'web-portal/src/content/blog'
public_images_dir = 'web-portal/public'

if not os.path.exists(blog_dir):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    blog_dir = os.path.join(base_dir, 'web-portal', 'src', 'content', 'blog')
    public_images_dir = os.path.join(base_dir, 'web-portal', 'public')

# List of files to delete based on the approved manual analysis
files_to_delete = [
    # 1. Off-policy / Irrelevant news
    'yayin-platformlarinin-yeni-krallari-nielsenden-izlenme-veril.md',
    'yeni-elektrikli-mercedes-cla-350-gercek-dunya-testlerinde-me.md',
    'luks-ve-guc-yeniden-tanimlaniyor-rolls-royce-spectre-series.md',
    'luksun-elektrikli-gelecegi-rolls-royce-spectre-series-ii-tan.md',
    'doganin-gizli-pusulasi-guvercinlerin-yon-bulma-sirri-karacig.md',
    'sigorta-teknolojisinde-devrim-sure-yapay-zeka-destekli-model-baglam-protokolu-ile-sektoru-donusturuyor.md',
    'livewire-dust-moto-satin-alimiyla-elektrikli-motosiklet-duny.md',
    'yapay-zekada-dev-hamle-softbank-fransaya-75-milyar-euroluk-y.md',
    'alphabetten-dev-hamle-yapay-zek-yarisi-icin-80-milyar-dolarl.md',
    'yapay-zekada-yeni-donem-alphabetten-80-milyar-dolarlik-altya.md',
    'anthropicten-yapay-zeka-arenasinda-tarihi-hamle-degerlemesi.md',
    'anthropicten-yapay-zeka-dunyasini-sallayan-dev-hamle-965-mil.md',
    'yapay-zeka-faturalarinda-dev-surpriz-kontrolsuz-kullanim-yarim-milyar-dolara-mal-oldu.md',
    'yapay-zeka-faturasi-sirketleri-soka-ugratiyor-kontrolsuz-claude-kullaniminin-maliyeti-yarim-milyar-dolari-bulabilir.md',
    'yapay-zeka-harcamalarinda-donum-noktasi-kurumsal-kullanim-maliyetleri-mercek-altinda.md',
    'yapay-zeka-harcamalarinda-sok-edici-gercek-bir-sirketin-clau.md',
    'yapay-zeka-harcamalarinda-yeni-bir-boyut-claude-icin-tek-ayd.md',

    # 2. Duplicate news (Fable Remake ertelemesi)
    'albiona-donus-erteleniyor-yeni-fable-icin-2027-cikis-tarihi.md',
    'fable-hayranlarini-uzecek-haber-efsanevi-rpgnin-cikisi-2027y.md',
    'fable-icin-yeni-bir-bekleyis-basladi-gelistirici-ekip-oyunu.md',
    'fable-remakein-beklenen-macerasi-2027ye-ertelendi-oyunculara.md',
    'fable-remakein-cikis-tarihi-resmi-olarak-gelecek-yila-ertele.md',
    'fable-yeniden-yapimi-icin-bekleyis-uzuyor-2027-hedefleniyor.md',
    'fablein-buyulu-dunyasina-giris-2027ye-uzadi-resmi-aciklama-g.md',
    'fablein-fantastik-dunyasina-yolculuk-uzuyor-cikis-tarihi-202.md',
    'fantastik-diyarin-kapilari-kapaniyor-fable-ertelendi-bekleyi.md',

    # 3. Duplicate news (Meta Akıllı Gözlük/Kolye)
    'meta-giyilebilir-teknoloji-arenasinda-vites-buyutuyor-akilli.md',
    'metadan-boyna-takilabilir-yapay-zeka-cihazi-kisisel-asistan.md',
    'metadan-yeni-nesil-yapay-zeka-hamlesi-boyna-takilabilir-akil.md',
    'metanin-giyilebilir-yapay-zeka-atilimi-yeni-nesil-asistan-bo.md',
    'metadan-cigir-acan-hamle-yapay-zeka-destekli-giyilebilir-asi.md',

    # 4. Duplicate news (Hands Over Korku Oyunu)
    'hands-over-duyuruldu-cocukluk-oyunlari-artik-birer-korku-deneyimi.md',
    'hands-over-ile-oyun-alanlari-olumcul-bir-kabusa-donusuyor-ye.md',
    'gizem-perdesi-aralaniyor-hands-overdan-ilk-ekran-goruntuleri-nefes-kesti.md',
    'oyun-dunyasinda-yeni-bir-soluk-hands-overdan-ilk-ekran-gorun.md',
    'parti-korkusuna-yeni-bir-soluk-hands-over-resmen-duyuruldu.md',

    # 5. Duplicate news (Call of Duty: Modern Warfare 4)
    'call-of-duty-modern-warfare-4-tanitim-fragmaniyla-rekorlari.md',
    'call-of-duty-modern-warfare-4te-radikal-degisim-gercekcilik.md',
    'call-of-duty-modern-warfare-serisinin-yeni-halkasindan-carpi.md',
    'modern-warfare-4ten-radikal-karar-absurt-skinler-ve-komik-ic.md',

    # 6. Duplicate news (The Witcher 3 / Witcher 4)
    'the-witcher-3-songs-of-the-past-genislemesinden-ilk-hikaye-d.md',
    'the-witcher-3un-yeni-genislemesi-songs-of-the-past-beklentil.md',
    'the-witcher-3un-yeni-projesi-the-witcher-4e-gizemli-bir-kopr.md',

    # 7. Duplicate news (Sega Streets of Rage)
    'seganin-kult-efsanesi-streets-of-rage-beyaz-perdeye-tasiniyo.md',
    'sokaklarin-efendileri-geri-donuyor-streets-of-rage-filminin.md',

    # 8. Duplicate news (BYD Otonom Sürüş Güvence)
    'byd-otonom-suruste-guvenceyi-yeniden-tanimliyor-sektorde-bir.md',
    'bydden-otonom-suruse-guven-tazeleyen-hamle-kaza-maliyetleri.md',
    'bydden-otonom-suruse-yeni-bir-guvence-anlayisi-kaza-sorumlul.md',

    # 9. Duplicate news (Apple Music Ücretsiz Katman)
    'apple-musicin-gelecegi-sekilleniyor-farkli-abonelik-katmanla.md',
    'apple-musicte-yeni-donem-ucretsiz-kullanim-secenegi-yolda-mi.md',

    # 10. Duplicate news (Yapısal Olmayan Veri Analizi)
    'yapisal-olmayan-veri-analizinde-yeni-bir-cag-ai-ve-buyuk-dil.md',
    'yapisal-olmayan-verinin-gizemini-cozmek-yapay-zeka-ile-derin.md',
    'yapisal-olmayan-verinin-gizemli-dunyasi-yapay-zeka-ile-donus.md',

    # 11. Duplicate news (Metin2 TR Affı)
    'metin2-trde-ikinci-sans-donemi-banli-hesaplar-icin-geri-donu.md',

    # 12. Duplicate news (Xiaomi HyperOS 3.1)
    'xiaomi-hyperos-31-kuresel-yayilimini-hizlandiriyor-yeni-nesil-deneyim-genis-kitlelere-ulasiyor.md',

    # 13. Duplicate news (Stuntman Hollywood)
    'saber-interactiveden-surpriz-hamle-stuntman-hollywood-ile-ik.md',
    'sinema-perdesi-direksiyona-tasiniyor-stuntman-hollywood-sahn.md',

    # 14. Duplicate news (Minecraft Filmi)
    'minecraft-filminden-gelen-yeni-goruntulerle-bloklar-beyaz-pe.md',
    'minecraft-sinematik-macerasi-devam-ediyor-yeni-filmin-adi-ve.md',

    # 15. Duplicate news (Minecraft Platform ESRB Sızıntısı)
    'minecraftin-yeni-duragi-belli-mi-oldu-esrb-sizintilari-buyuk.md',

    # 16. Duplicate news (Planet Zoo 2)
    'planet-zoo-2den-goz-alici-ekran-goruntuleri-sizdi-sanal-hayv.md',
    'planet-zoo-2den-ilk-bakis-hayvanat-bahcesi-simulasyonunun-gelecegi-sekilleniyor.md',

    # 17. Duplicate news (Google Pixel Watch 5 prototipi su altında)
    'sualti-surprizi-tanitilmayan-pixel-watch-5-prototipi-kesfedi.md',

    # 18. Duplicate news (Honor Win Turbo)
    'honor-win-turbo-tanitildi-dev-batarya-ve-guclu-donanimin-bulustugu-yeni-nesil-akilli-telefon.md',

    # 19. Duplicate news (HONOR X7e)
    'honorun-butce-dostu-yeni-uyesi-honor-x7e-tanitildi.md',

    # 20. Duplicate news (Samsung Galaxy Z Fold 8)
    'samsung-galaxy-z-fold8-ilk-kez-goruntulendi-katlanabilir-ekr.md',

    # 21. Duplicate news (Asus Wi-Fi 8 GT-BN98 Pro / ROG Rapture)
    'asus-wi-fi-8-cagini-baslatiyor-rog-rapture-gt-bn98-pro-oyunc.md',

    # 22. Duplicate news (Martin Scorsese Yapay Zeka)
    'sinemanin-ustasi-martin-scorseseden-vizyoner-adim-storyboard.md',

    # 23. Duplicate news (GeForce Now)
    'geforce-nowa-bu-hafta-eklenen-yeni-oyunlar-aciklandi-bulut-o.md',

    # 24. Duplicate news (Amazon Prime Gaming)
    'amazon-prime-oyun-kutuphanesi-genisliyor-haziran-ayi-listesi.md',

    # 25. Duplicate news (Xbox Game Pass)
    'xbox-game-pass-kutuphanesi-genisliyor-haziran-ayinin-yeni-oy.md',

    # 26. Duplicate news (Android / Apple dosya paylaşımı)
    'android-dunyasinda-airdrop-deneyimi-hizli-ve-kolay-dosya-pay.md',
    'android-ve-iphone-arasindaki-sinirlar-kalkiyor-genisletilmis.md',
]

deleted_markdowns_count = 0
deleted_images_count = 0

for file_to_delete in files_to_delete:
    markdown_path = os.path.join(blog_dir, file_to_delete)
    
    if os.path.exists(markdown_path):
        # Read the file first to find the image field
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Match the image field
            image_match = re.search(r'^image:\s*(["\'])(.*?)\1\s*$', content, re.MULTILINE)
            if not image_match:
                image_match = re.search(r'^image:\s*(.*?)\s*$', content, re.MULTILINE)
            
            if image_match:
                image_relative_path = image_match.group(2) if len(image_match.groups()) >= 2 else image_match.group(1)
                image_relative_path = image_relative_path.strip('\'" ')
                
                # Check if it starts with /images/
                if image_relative_path.startswith('/'):
                    image_relative_path = image_relative_path[1:] # remove leading slash
                
                image_full_path = os.path.join(public_images_dir, image_relative_path)
                
                # Delete the image if it exists and is a local image under public
                if os.path.exists(image_full_path) and os.path.isfile(image_full_path):
                    try:
                        os.remove(image_full_path)
                        print(f"Silinen Resim: {image_relative_path}")
                        deleted_images_count += 1
                    except Exception as e:
                        print(f"Resim silinemedi {image_relative_path}: {e}")
        
        # Now delete the markdown file itself
        try:
            os.remove(markdown_path)
            print(f"Silinen Haber: {file_to_delete}")
            deleted_markdowns_count += 1
        except Exception as e:
            print(f"Haber silinemedi {file_to_delete}: {e}")
    else:
        print(f"Haber bulunamadı (zaten silinmiş olabilir): {file_to_delete}")

print(f"\nTemizlik Tamamlandı!")
print(f"Silinen Haber Sayısı: {deleted_markdowns_count}")
print(f"Silinen Resim Sayısı: {deleted_images_count}")
