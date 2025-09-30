import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi

# Referanslar
motor_ref = None
sensor_ref = None

# Ürün verileri
gecici_barkod = None
gecici_agirlik = None
gecici_urun_uzunlugu = None

# Durum kontrolü
barkod_lojik = False
agirlik_lojik = False
gso_bekleniyor = False
yonlendirici_giris_aktif = False

# İade durumu
iade_aktif = False
iade_gsi_bekliyor = False
iade_gso_bekliyor = False

# Kabul edilen ürünler kuyruğu
kabul_edilen_urunler = deque()

def motor_referansini_ayarla(motor):
    global motor_ref
    motor_ref = motor
    motor_ref.motorlari_aktif_et()
    motor_ref.konveyor_dur()
    sistem_sifirla()
    print("✅ Motor hazır - Sistem başlatıldı")

def sensor_referansini_ayarla(sensor):
    global sensor_ref
    sensor_ref = sensor

def sistem_sifirla():
    """Tüm sistem durumlarını sıfırlar"""
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor
    global barkod_lojik, agirlik_lojik, gso_bekleniyor, yonlendirici_giris_aktif
    global gecici_barkod, gecici_agirlik, gecici_urun_uzunlugu
    
    iade_aktif = False
    iade_gsi_bekliyor = False
    iade_gso_bekliyor = False
    barkod_lojik = False
    agirlik_lojik = False
    gso_bekleniyor = False
    yonlendirici_giris_aktif = False
    gecici_barkod = None
    gecici_agirlik = None
    gecici_urun_uzunlugu = None
    
    if sensor_ref:
        sensor_ref.led_ac()
    
    print("🔄 [SİSTEM] Durum sıfırlandı - Yeni ürün bekliyor\n")


def agirlik_verisi_al(agirlik):
    global agirlik_lojik, gecici_agirlik, gso_bekleniyor, iade_aktif
    
    # İade aktifse yeni ağırlık işleme
    if iade_aktif:
        print(f"🚫 [İADE AKTIF] Ağırlık görmezden gelindi: {agirlik}gr")
        return
    
    agirlik_lojik = True
    gecici_agirlik = agirlik
    print(f"⚖️  [AĞIRLIK] Ölçülen: {agirlik}gr")
    
    if gso_bekleniyor:
        print(f"🔍 [DOĞRULAMA] GSO sonrası kontrol başlıyor...")
        gso_sonrasi_dogrulama()
        gso_bekleniyor = False

def barkod_verisi_al(barcode):
    global barkod_lojik, gecici_barkod, iade_aktif
    
    # İade aktifse yeni barkod işleme
    if iade_aktif:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return
    
    # Eğer zaten bir barkod varsa yeni barkodu reddet
    if barkod_lojik and gecici_barkod:
        print(f"🚫 [BARKOD MEVCUT] Zaten işlenen barkod var: {gecici_barkod}")
        print(f"🚫 [REDDEDİLDİ] Yeni barkod reddedildi: {barcode}")
        return
    
    barkod_lojik = True
    gecici_barkod = barcode
    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}")
    
    # Barkod gelince hemen veritabanı kontrolü
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(barcode)
    if urun_bilgisi:
        materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
        materyal_adi = materyal_isimleri.get(urun_bilgisi.get('material'), "BİLİNMEYEN")
        print(f"✅ [VERİTABANI] Ürün tanındı: {materyal_adi}")
    else:
        print(f"❌ [VERİTABANI] Ürün bulunamadı: {barcode}")

def uzunluk_verisi_al(uzunluk_str):
    global gecici_urun_uzunlugu, iade_aktif
    try:
        gecici_urun_uzunlugu = float(uzunluk_str.replace(",", "."))
        print(f"📏 [UZUNLUK] Ölçülen: {gecici_urun_uzunlugu}mm")
        
    except:
        print(f"❌ [HATA] Uzunluk verisi hatalı: {uzunluk_str}")

def agirlik_kontrol(urun_bilgisi, agirlik):
    """Ağırlık tolerans kontrolü (±25gr)"""
    min_agirlik = urun_bilgisi.get('packMinWeight')
    max_agirlik = urun_bilgisi.get('packMaxWeight')
    
    if not min_agirlik or not max_agirlik:
        return True  # Sınır yoksa kabul et
    
    tolerans = 25
    return (min_agirlik - tolerans) <= agirlik <= (max_agirlik + tolerans)

def urun_kabul_et(barkod, agirlik, materyal_id):
    """Ürünü kuyruğa ekler"""
    urun = {
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_id': materyal_id,
        'zaman': time.time()
    }
    kabul_edilen_urunler.append(urun)
    materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
    materyal_adi = materyal_isimleri.get(materyal_id, "BİLİNMEYEN")
    print(f"✅ [KABUL] {materyal_adi} ürün kuyruğa eklendi | Toplam: {len(kabul_edilen_urunler)}")

def urun_iade_et(sebep):
    """Ürünü iade eder"""
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor
    global barkod_lojik, agirlik_lojik, gecici_barkod, gecici_agirlik
    
    print(f"\n❌ [İADE BAŞLADI] Sebep: {sebep}")
    
    # İade başlarken tüm geçici verileri temizle
    print(f"🧹 [TEMİZLEME] İade sırasındaki veriler temizleniyor")
    barkod_lojik = False
    agirlik_lojik = False
    gecici_barkod = None
    gecici_agirlik = None
    
    print(f"🔄 [MOTOR] Konveyör geri dönmeye başladı")
    iade_aktif = True
    motor_ref.konveyor_geri()

    iade_gsi_bekliyor = True
    print(f"⏳ [İADE] GSI sensörü bekleniyor...")

def iade_tamamla():
    """İade işlemini bitirir"""
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor
    global barkod_lojik, agirlik_lojik, gecici_barkod, gecici_agirlik, gso_bekleniyor
    
    print(f"\n✅ [İADE BİTTİ] Ürün kullanıcı tarafından alındı")
    
    # Durumları sıfırla
    iade_aktif = False
    iade_gsi_bekliyor = False 
    iade_gso_bekliyor = False
    barkod_lojik = False
    agirlik_lojik = False
    gecici_barkod = None
    gecici_agirlik = None
    gso_bekleniyor = False
    
    print(f"🔄 [SİSTEM] Durum sıfırlandı - Yeni ürün kabul edilebilir")
    print(f"🎯 [HAZIR] Sistem bekleme modunda\n")

def gso_sonrasi_dogrulama():
    """GSO sonrası ürün doğrulaması"""
    global gecici_barkod, gecici_agirlik
    
    print(f"\n🔍 [DOĞRULAMA BAŞLADI] GSO sonrası kontrol")
    
    if not gecici_barkod:
        print(f"❌ [DOĞRULAMA] Barkod verisi yok")
        veri_temizle()
        return
    
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(gecici_barkod)
    
    if not urun_bilgisi:
        print(f"❌ [DOĞRULAMA] Veritabanında ürün bulunamadı")
        urun_iade_et("Ürün bulunamadı")
        veri_temizle()
        return
    
    # Ağırlık kontrolü
    print(f"⚖️ [DOĞRULAMA] Ağırlık kontrolü yapılıyor...")
    if not agirlik_kontrol(urun_bilgisi, gecici_agirlik):
        print(f"❌ [DOĞRULAMA] Ağırlık tolerans dışında")
        urun_iade_et("Ağırlık uyumsuz")
        veri_temizle()
        return
    
    # Ürün kabul edildi
    materyal_id = urun_bilgisi.get('material')
    print(f"✅ [DOĞRULAMA] Tüm kontroller başarılı")
    urun_kabul_et(gecici_barkod, gecici_agirlik, materyal_id)
    
    # Konveyörü ilerlet
    if motor_ref:
        motor_ref.konveyor_ileri()
        print(f"▶️ [MOTOR] Ürün kabul edildi - Konveyör ilerliyor")
    
    veri_temizle()   

def veri_temizle():
    """Geçici verileri temizler"""
    global barkod_lojik, agirlik_lojik, gecici_barkod, gecici_agirlik
    barkod_lojik = False
    agirlik_lojik = False
    gecici_barkod = None
    gecici_agirlik = None

def yonlendirici_karar_ver():
    """FIFO kuyruğundan ürün alıp yönlendirir"""
    global yonlendirici_giris_aktif, gecici_urun_uzunlugu
    
    if not kabul_edilen_urunler:
        motor_ref.konveyor_dur()
        print("❌ [YÖNLENDİRİCİ] Kuyrukta ürün yok")
        return
    
    # En eski ürünü al
    urun = kabul_edilen_urunler.popleft()
    materyal_id = urun.get('materyal_id')
    
    materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
    materyal_adi = materyal_isimleri.get(materyal_id, "BİLİNMEYEN")
    
    print(f"\n🔄 [YÖNLENDİRME] {materyal_adi} ürün işleniyor: {urun['barkod']}")
    print(f"📦 [KUYRUK] Kalan ürün sayısı: {len(kabul_edilen_urunler)}")
    
    if motor_ref:
        if materyal_id == 2:  # Cam
            motor_ref.yonlendirici_cam()
            print(f"🟦 [CAM] Cam yönlendiricisine gönderildi")
        else:  # Plastik/Metal
            motor_ref.yonlendirici_plastik() 
            print(f"🟩 [PLASTİK] Plastik yönlendiricisine gönderildi")
    
    # Temizle
    yonlendirici_giris_aktif = False
    gecici_urun_uzunlugu = None
    
    print(f"✅ [YÖNLENDİRME] İşlem tamamlandı\n")

# Ana olay işleyici
def olayi_isle(olay):
    global gso_bekleniyor, yonlendirici_giris_aktif
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor
    
    print(f"\n📨 [OLAY] {olay}")
    
    # İade işlemi aktifse
    if iade_aktif:
        if olay.strip().lower() == "gsi":
            print(f"✅ [İADE-GSI] Sensör tetiklendi - 0.2s daha geri dönüyor")
            time.sleep(0.2)
            motor_ref.konveyor_dur()
            print(f"⏹️ [İADE] Motor durdu - GSO bekleniyor")
            return
            
        elif olay.strip().lower() == "gso":
            print(f"✅ [İADE-GSO] Çıkış sensörü tetiklendi - Ürün alındı")
            iade_tamamla()
            return
        else:
            print(f"🚫 [İADE AKTIF] {olay} olayı görmezden gelindi")
            return

    
    # Normal işlemler
    olay = olay.strip().lower()
    
    if olay == "oturum_var":
        print(f"🟢 [OTURUM] Aktif oturum başlatıldı")
        if sensor_ref:
            sensor_ref.led_ac()
    
    elif olay.startswith("a:"):
        agirlik = float(olay.split(":")[1].replace(",", "."))
        agirlik_verisi_al(agirlik)
    
    elif olay.startswith("m:"):
        uzunluk_str = olay.split(":")[1]
        uzunluk_verisi_al(uzunluk_str)
    
    elif olay == "gsi":
        motor_ref.konveyor_ileri()
        print(f"▶️ [MOTOR] Giriş sensör algılandı. Konveyör ileri hareket başladı")
    
    elif olay == "ysi":
        print(f"� [YSI] Yönlendirici giriş sensörü tetiklendi")
    
    elif olay == "yso":
        print(f"🟠 [YSO] Yönlendirici çıkış sensörü tetiklendi")
        if gecici_urun_uzunlugu is not None:
            yonlendirici_karar_ver()
        else:
            print(f"⏳ [YÖNLENDİRİCİ] Uzunluk verisi bekleniyor...")
    
    elif olay == "gso":
        print(f"� [GSO] Çıkış sensörü tetiklendi - Kontrol başlıyor")
        if not barkod_lojik:
            print(f"❌ [KONTROL] Barkod verisi yok")
            if not kabul_edilen_urunler:
                urun_iade_et("Barkod yok")
                veri_temizle()
            else:
                print(f"❌ [KONTROL] Ancak kuyrukta ürün var, iade edilmedi")
                veri_temizle()
        else:
            gso_bekleniyor = True
            print(f"⏳ [KONTROL] Güncel ağırlık verisi bekleniyor...")

sistem_durumunu_sifirla = sistem_sifirla