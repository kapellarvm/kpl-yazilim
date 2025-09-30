import time
from collections import deque

from ...veri_tabani import veritabani_yoneticisi

# Global motor referansı (seri_deneme.py'den ayarlanacak)
motor_ref = None
sensor_ref = None

# Giriş mantık değişkenleri
agirlik_lojik = False
barkod_lojik = False

# Geçici veri saklama
gecici_barkod = None
gecici_agirlik = None

# Durum kontrolü
gso_bekleniyor = False  # GSO sonrası ağırlık bekleme durumu

# Yönlendirici sensör durumları
yonlendirici_giris_aktif = False  # YSI - Yönlendiriciye giriş
gecici_urun_uzunlugu = None      # m:213,15 formatındaki uzunluk verisi

# Kabul edilen ürünler kuyruğu (FIFO - Queue)
kabul_edilen_urunler = deque()

def motor_referansini_ayarla(motor):
    global motor_ref
    motor_ref = motor
    motor_ref.motorlari_aktif_et()

def sensor_referansini_ayarla(sensor):
    global sensor_ref
    sensor_ref = sensor
    
def agirlik_verisi_al(agirlik):
    global agirlik_lojik, gecici_agirlik, gso_bekleniyor
    agirlik_lojik = True
    gecici_agirlik = agirlik
    print(f"[Oturum Var] Alınan ağırlık verisi: {agirlik} gram")
    
    # Eğer GSO sonrası ağırlık bekliyorsak, şimdi doğrulama yap
    if gso_bekleniyor:
        print(f"[Oturum Var] GSO sonrası ağırlık verisi alındı - Doğrulama başlatılıyor")
        gso_sonrasi_dogrulama()
        gso_bekleniyor = False

def barkod_verisi_al(barcode):
    global barkod_lojik, gecici_barkod
    barkod_lojik = True
    gecici_barkod = barcode
    print(f"[Oturum Var] Alınan barkod verisi: {barcode}")
    veri_tabani_dogrulama(barcode)

def uzunluk_verisi_al(uzunluk_str):
    """
    m:213,15 formatındaki uzunluk verisini alır ve işler.
    """
    global gecici_urun_uzunlugu
    try:
        # "213,15" kısmını al ve float'a çevir
        uzunluk = float(uzunluk_str.replace(",", "."))
        gecici_urun_uzunlugu = uzunluk
        print(f"[Oturum Var] Alınan ürün uzunluğu: {uzunluk} mm")
        
        # Uzunluk verisi gelince yönlendirme işlemini başlat
        if yonlendirici_giris_aktif:
            yonlendirici_karar_ver()
            
    except ValueError as e:
        print(f"[Oturum Var] ❌ Uzunluk verisi işlenirken hata: {e}")
        gecici_urun_uzunlugu = None


def veri_tabani_dogrulama(barcode):
    """
    Gelen barkod verisini veritabanında bulup ürün bilgilerini print eder.
    """
    print(f"[Veritabanı Doğrulama] Barkod sorgulanıyor: {barcode}")
    
    # Veritabanından barkod bilgilerini al
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(barcode)
    
    if urun_bilgisi:
        print(f"[Veritabanı Doğrulama] ✅ Ürün bulundu!")
        print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ ÜRÜN BİLGİLERİ")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ ID: {urun_bilgisi.get('id', 'Bilinmiyor')}")
        print(f"║ Barkod: {urun_bilgisi.get('barcode', 'Bilinmiyor')}")
        print(f"║ Materyal ID: {urun_bilgisi.get('material', 'Bilinmiyor')}")
        
        # Materyal ID'sini anlamlı isme çevirme
        materyal_isimleri = {
            1: "PET",
            2: "Cam (Glass)", 
            3: "Alüminyum (Alu)"
        }
        materyal_adi = materyal_isimleri.get(urun_bilgisi.get('material'), "Bilinmeyen Materyal")
        print(f"║ Materyal Türü: {materyal_adi}")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ AĞIRLIK BİLGİLERİ")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        
        min_agirlik = urun_bilgisi.get('packMinWeight')
        max_agirlik = urun_bilgisi.get('packMaxWeight')
        print(f"║ Minimum Ağırlık: {min_agirlik if min_agirlik is not None else 'Belirtilmemiş'} gr")
        print(f"║ Maksimum Ağırlık: {max_agirlik if max_agirlik is not None else 'Belirtilmemiş'} gr")
        
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ BOYUT BİLGİLERİ")
        print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
        
        min_genislik = urun_bilgisi.get('packMinWidth')
        max_genislik = urun_bilgisi.get('packMaxWidth')
        min_yukseklik = urun_bilgisi.get('packMinHeight')
        max_yukseklik = urun_bilgisi.get('packMaxHeight')
        
        print(f"║ Minimum Genişlik: {min_genislik if min_genislik is not None else 'Belirtilmemiş'} mm")
        print(f"║ Maksimum Genişlik: {max_genislik if max_genislik is not None else 'Belirtilmemiş'} mm")
        print(f"║ Minimum Yükseklik: {min_yukseklik if min_yukseklik is not None else 'Belirtilmemiş'} mm")
        print(f"║ Maksimum Yükseklik: {max_yukseklik if max_yukseklik is not None else 'Belirtilmemiş'} mm")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
                
        return urun_bilgisi
    else:
        print(f"[Veritabanı Doğrulama] ❌ Ürün bulunamadı: {barcode}")
        print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
        print(f"║ HATA: Barkod '{barcode}' veritabanında kayıtlı değil!")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
        return None

def agirlik_dogrulama(urun_bilgisi, olculen_agirlik):
    """
    Ölçülen ağırlığı veritabanındaki değerlerle karşılaştırır.
    ±10gr toleransla kabul/red kararı verir.
    """
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ AĞIRLIK DOĞRULAMA")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    
    min_agirlik = urun_bilgisi.get('packMinWeight')
    max_agirlik = urun_bilgisi.get('packMaxWeight')
    
    print(f"║ Ölçülen Ağırlık: {olculen_agirlik} gr")
    print(f"║ Beklenen Aralık: {min_agirlik if min_agirlik else 'Yok'} - {max_agirlik if max_agirlik else 'Yok'} gr")
    print(f"║ Tolerans: ±10 gr")
    
    # Ağırlık sınırları yoksa sadece uyarı ver, kabul et
    if min_agirlik is None and max_agirlik is None:
        print(f"║ ⚠️  Ağırlık sınırları tanımlı değil - KABUL EDİLDİ")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
        return True
    
    # Toleranslı sınırları hesapla
    tolerans = 10
    min_limit = (min_agirlik - tolerans) if min_agirlik else 0
    max_limit = (max_agirlik + tolerans) if max_agirlik else float('inf')
    
    print(f"║ Toleranslı Aralık: {min_limit} - {max_limit} gr")
    
    # Ağırlık kontrolü
    if min_limit <= olculen_agirlik <= max_limit:
        print(f"║ ✅ AĞIRLIK DOĞRULAMA BAŞARILI")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
        return True
    else:
        print(f"║ ❌ AĞIRLIK DOĞRULAMA BAŞARISIZ")
        if olculen_agirlik < min_limit:
            print(f"║ Sebep: Ürün çok hafif ({olculen_agirlik} < {min_limit})")
        else:
            print(f"║ Sebep: Ürün çok ağır ({olculen_agirlik} > {max_limit})")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
        return False

def goruntu_dogrulama_placeholder(urun_bilgisi):
    """
    Gelecekte görüntü işleme verilerini doğrulayacak fonksiyon.
    Şu anda placeholder olarak True döner.
    """
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ GÖRÜNTÜ DOĞRULAMA (PLACEHOLDER)")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ 🔮 Gelecekte eklenecek:")
    print(f"║ • Materyal türü karşılaştırması")
    print(f"║ • Genişlik doğrulaması")
    print(f"║ • Uzunluk doğrulaması")
    print(f"║ • Yükseklik doğrulaması")
    print(f"║")
    print(f"║ ⚠️  Şimdilik tüm görüntü doğrulamaları KABUL EDİLİYOR")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
    return True

def uzunluk_dogrulama_placeholder(urun_bilgisi, olculen_uzunluk):
    """
    Ölçülen uzunluğu veritabanındaki değerlerle karşılaştırır.
    Şu anda placeholder olarak toleranslı kontrol yapar ama True döner.
    """
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ UZUNLUK DOĞRULAMA (PLACEHOLDER)")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    
    min_uzunluk = urun_bilgisi.get('packMinHeight')  # Şimdilik height kullanıyoruz
    max_uzunluk = urun_bilgisi.get('packMaxHeight')
    
    print(f"║ Ölçülen Uzunluk: {olculen_uzunluk} mm")
    print(f"║ Beklenen Aralık: {min_uzunluk if min_uzunluk else 'Yok'} - {max_uzunluk if max_uzunluk else 'Yok'} mm")
    print(f"║ Tolerans: ±20 mm")
    
    # Uzunluk sınırları yoksa sadece uyarı ver
    if min_uzunluk is None and max_uzunluk is None:
        print(f"║ ⚠️  Uzunluk sınırları tanımlı değil")
    else:
        # Toleranslı sınırları hesapla (ama sonuç her zaman True)
        tolerans = 20
        min_limit = (min_uzunluk - tolerans) if min_uzunluk else 0
        max_limit = (max_uzunluk + tolerans) if max_uzunluk else float('inf')
        
        print(f"║ Toleranslı Aralık: {min_limit} - {max_limit} mm")
        
        # Gerçek kontrol yapılıyor ama sonuç görmezden geliniyor
        if min_limit <= olculen_uzunluk <= max_limit:
            print(f"║ ✅ Uzunluk aralık içinde (ama placeholder)")
        else:
            print(f"║ ⚠️  Uzunluk aralık dışında (ama placeholder)")
    
    print(f"║ 🔮 Gelecekte görüntü işleme ile gerçek kontrol yapılacak")
    print(f"║ ⚠️  Şimdilik tüm uzunluk doğrulamaları KABUL EDİLİYOR")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
    return True

def urun_kabulü(barkod, agirlik, urun_bilgisi):
    """
    Ürünü kabul edilen ürünler kuyruğuna ekler.
    """
    global kabul_edilen_urunler
    
    urun_verisi = {
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_id': urun_bilgisi.get('material'),
        'kabul_zamani': time.time()
    }
    
    kabul_edilen_urunler.append(urun_verisi)
    
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ ÜRÜN KABULÜ")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ ✅ ÜRÜN KABUL EDİLDİ VE KUYRUĞA EKLENDİ")
    print(f"║ Barkod: {barkod}")
    print(f"║ Ağırlık: {agirlik} gr")
    print(f"║ Materyal: {urun_bilgisi.get('material')}")
    print(f"║ Kuyruktaki Ürün Sayısı: {len(kabul_edilen_urunler)}")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════")

def giris_iade(sebep="Bilinmeyen sebep"):

    global agirlik_lojik, barkod_lojik, gecici_barkod, gecici_agirlik, motor_ref

    """
    Ürün iade edilir.
    """
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ İADE İŞLEMİ")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ ❌ ÜRÜN İADE EDİLDİ")
    print(f"║ Sebep: {sebep}")
    print(f"║ Ağırlık Verisi: {'✅ Var' if agirlik_lojik else '❌ Yok'}")
    print(f"║ Barkod Verisi: {'✅ Var' if barkod_lojik else '❌ Yok'}")
    if gecici_barkod:
        print(f"║ Barkod: {gecici_barkod}")
    if gecici_agirlik:
        print(f"║ Ağırlık: {gecici_agirlik} gr")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
    
    # Motor ile ürünü geri gönder
    if motor_ref:
        print("[Giriş İade] Ürün konveyör ile geri gönderiliyor...")
        motor_ref.konveyor_dur()
        print("[Giriş İade] Ürün iade edildi.")
    else:
        print("[Giriş İade] Motor referansı bulunamadı.")

def gso_sonrasi_dogrulama():
    """
    GSO sonrası gelen güncel ağırlık verisi ile doğrulama yapar.
    """
    global gecici_barkod, gecici_agirlik, agirlik_lojik, barkod_lojik
    
    print("[Oturum Var] ✅ Güncel verilerle doğrulama işlemi başlatılıyor")
    
    # Veritabanından ürün bilgilerini al
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(gecici_barkod)
    
    if urun_bilgisi is None:
        print("[Oturum Var] ❌ Ürün veritabanında bulunamadı")
        giris_iade("Ürün veritabanında kayıtlı değil")
    else:
        # Ağırlık doğrulaması
        agirlik_gecerli = agirlik_dogrulama(urun_bilgisi, gecici_agirlik) if gecici_agirlik else False
        
        # Görüntü doğrulaması (placeholder)
        goruntu_gecerli = goruntu_dogrulama_placeholder(urun_bilgisi)
        
        # Tüm doğrulamalar başarılıysa ürünü kabul et
        if agirlik_gecerli and goruntu_gecerli:
            urun_kabulü(gecici_barkod, gecici_agirlik, urun_bilgisi)
            
            # Motor ile ürünü ilerlet
            if motor_ref:
                print("[Oturum Var] Ürün kabul edildi, konveyör ilerletiliyor...")
                motor_ref.konveyor_ileri()
        else:
            # Doğrulama başarısızsa iade et
            sebep_listesi = []
            if not agirlik_gecerli:
                sebep_listesi.append("Ağırlık uyumsuzluğu")
            if not goruntu_gecerli:
                sebep_listesi.append("Görüntü uyumsuzluğu")
            
            sebep = ", ".join(sebep_listesi)
            giris_iade(sebep)
    
    # Kontrol sonrası değişkenleri sıfırla
    agirlik_lojik = False
    barkod_lojik = False
    gecici_barkod = None
    gecici_agirlik = None

def yonlendirici_karar_ver():
    """
    Yönlendiriciye giren ürünün materyal türüne göre yönlendirme yapar.
    FIFO mantığıyla kabul edilen ürünler kuyruğundan en eski ürünü alır ve kuyruktan çıkarır.
    """
    global gecici_urun_uzunlugu, yonlendirici_giris_aktif, kabul_edilen_urunler
    
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ YÖNLENDİRİCİ KARAR SİSTEMİ")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    
    # Kuyruk boşsa işlem yapma
    if not kabul_edilen_urunler:
        print(f"║ ❌ Kabul edilen ürün bulunamadı - Yönlendirme yapılamıyor")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
        return
    
    # FIFO: En eski ürünü al ve kuyruktan çıkar
    islenen_urun = kabul_edilen_urunler.popleft()
    materyal_id = islenen_urun.get('materyal_id')
    barkod = islenen_urun.get('barkod')
    agirlik = islenen_urun.get('agirlik')
    
    materyal_isimleri = {1: "PET", 2: "Cam (Glass)", 3: "Alüminyum (Alu)"}
    materyal_adi = materyal_isimleri.get(materyal_id, "Bilinmeyen")
    
    print(f"║ Barkod: {barkod}")
    print(f"║ Ağırlık: {agirlik} gr")
    print(f"║ Materyal: {materyal_adi} (ID: {materyal_id})")
    print(f"║ Kalan Kuyruk Uzunluğu: {len(kabul_edilen_urunler)}")
    
    if gecici_urun_uzunlugu:
        print(f"║ Ölçülen Uzunluk: {gecici_urun_uzunlugu} mm")
        print(f"║ ℹ️  Uzunluk verisi kaydedildi (görüntü işleme ile karşılaştırılacak)")
    else:
        print(f"║ ⚠️  Uzunluk verisi yok")
    
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    print(f"║ YÖNLENDİRME KARARI")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════")
    
    # Materyal türüne göre yönlendirme
    if materyal_id == 2:  # Cam
        print(f"║ 🔄 CAM ÜRÜN - Cam yönlendiricisine gönderiliyor")
        if motor_ref:
            motor_ref.yonlendirici_cam()
            print(f"║ ✅ Yönlendirici cam komutu gönderildi")
        else:
            print(f"║ ❌ Motor referansı bulunamadı")
    else:  # Plastik (PET) veya Metal (Alüminyum)
        materyal_tip = "PET" if materyal_id == 1 else "METAL" if materyal_id == 3 else "PLASTİK"
        print(f"║ 🔄 {materyal_tip} ÜRÜN - Plastik yönlendiricisine gönderiliyor")
        if motor_ref:
            motor_ref.yonlendirici_plastik()
            print(f"║ ✅ Yönlendirici plastik komutu gönderildi")
        else:
            print(f"║ ❌ Motor referansı bulunamadı")
    
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════")
    
    # İşlem tamamlandı, değişkenleri temizle
    yonlendirici_giris_aktif = False
    gecici_urun_uzunlugu = None

############################################## Senaryolar Alt Kısım (İşlem Fonksiyonları) ##############################################

def olayi_isle(olay):
    global agirlik_lojik, barkod_lojik, gecici_agirlik, gecici_barkod, yonlendirici_giris_aktif
    print(f"[Oturum Var] Gelen olay: {olay}")

    if olay.strip().lower() == "oturum_var":
        if sensor_ref:
            sensor_ref.led_ac()
        else:
            print("[Oturum Var] Sensor referansı bulunamadı.")

    if olay.strip().lower().startswith("a:"):
        agirlik_str = olay.split(":")[1]
        agirlik = float(agirlik_str.replace(",", "."))
        agirlik_verisi_al(agirlik)

    if olay.strip().lower().startswith("m:"):
        # m:213,15 formatındaki uzunluk verisi
        uzunluk_str = olay.split(":")[1]
        uzunluk_verisi_al(uzunluk_str)

    if olay.strip().lower() == "gsi":
        if motor_ref:
            motor_ref.konveyor_ileri()
            print("[Oturum Var] Motor aktif edildi.")
        else:
            print("[Oturum Var] Motor referansı bulunamadı.")

    if olay.strip().lower() == "ysi":
        # Yönlendiriciye giriş başladı
        yonlendirici_giris_aktif = True
        print("[Oturum Var] ✅ Ürün yönlendiriciye girmeye başladı (YSI)")
        print("[Oturum Var] ⏳ Yönlendirici sensörü tamamen geçilmesi bekleniyor...")

    if olay.strip().lower() == "yso":
        # Yönlendiriciye tamamen girdi
        print("[Oturum Var] ✅ Ürün yönlendiriciye tamamen girdi (YSO)")
        
        # Eğer uzunluk verisi varsa hemen karar ver, yoksa bekle
        if gecici_urun_uzunlugu is not None:
            print("[Oturum Var] ✅ Uzunluk verisi mevcut - Yönlendirme kararı veriliyor")
            yonlendirici_karar_ver()
        else:
            print("[Oturum Var] ⏳ Uzunluk verisi bekleniyor...")

    if olay.strip().lower() == "gso":
        global gso_bekleniyor
        print("[Oturum Var] GSO mesajı alındı - Giriş kontrol ediliyor...")
        
        # Barkod verisi kontrol et
        if not barkod_lojik:
            print("[Oturum Var] ❌ Barkod verisi yok - İade işlemi başlatılıyor")
            giris_iade("Barkod verisi bulunamadı")
            # Kontrol sonrası değişkenleri sıfırla
            agirlik_lojik = False
            barkod_lojik = False
            gecici_barkod = None
            gecici_agirlik = None
        else:
            print("[Oturum Var] ✅ Barkod verisi mevcut - Güncel ağırlık verisi bekleniyor...")
            # GSO sonrası ağırlık bekleme moduna geç
            gso_bekleniyor = True
            print("[Oturum Var] ⏳ Güncel ağırlık verisi için bekleniyor...")
        
    # Oturum yokken yapılacak diğer işlemler buraya eklenebilir