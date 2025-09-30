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
    
    print("🔄 Sistem sıfırlandı - Yeni ürün bekliyor")

def durum_raporu():
    """Sistem durumunu gösterir"""
    print(f"İade: {iade_aktif} | GSO: {gso_bekleniyor} | Barkod: {barkod_lojik} | Kuyruk: {len(kabul_edilen_urunler)}")

def agirlik_verisi_al(agirlik):
    global agirlik_lojik, gecici_agirlik, gso_bekleniyor
    agirlik_lojik = True
    gecici_agirlik = agirlik
    print(f"📊 Ağırlık: {agirlik}gr")
    
    if gso_bekleniyor:
        gso_sonrasi_dogrulama()
        gso_bekleniyor = False

def barkod_verisi_al(barcode):
    global barkod_lojik, gecici_barkod
    barkod_lojik = True
    gecici_barkod = barcode
    print(f"📋 Barkod: {barcode}")
    
    # Barkod gelince hemen veritabanı kontrolü
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(barcode)
    if urun_bilgisi:
        print(f"✅ Ürün tanındı: {urun_bilgisi.get('material')} tipi")
    else:
        print(f"❌ Ürün bulunamadı")

def uzunluk_verisi_al(uzunluk_str):
    global gecici_urun_uzunlugu
    try:
        gecici_urun_uzunlugu = float(uzunluk_str.replace(",", "."))
        print(f"📏 Uzunluk: {gecici_urun_uzunlugu}mm")
        
        if yonlendirici_giris_aktif:
            yonlendirici_karar_ver()
    except:
        print(f"❌ Uzunluk verisi hatalı: {uzunluk_str}")

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
    print(f"✅ Ürün kabul edildi | Kuyruk: {len(kabul_edilen_urunler)}")

def urun_iade_et(sebep, tip="timer"):
    """Ürünü iade eder"""
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor
    
    print(f"❌ İade: {sebep}")
    iade_aktif = True
    
    if motor_ref:
        motor_ref.konveyor_geri()
        
        if tip == "timer":
            # 2 saniye geri dön
            import threading
            def timer_stop():
                time.sleep(2.0)
                if motor_ref and iade_aktif:
                    motor_ref.konveyor_dur()
                    global iade_gso_bekliyor
                    iade_gso_bekliyor = True
                    print("⏹️ İade durduruldu - GSO bekliyor")
            threading.Thread(target=timer_stop, daemon=True).start()
            
        if tip == "gsi_bekle":
            iade_gsi_bekliyor = True
            print("⏳ GSI bekleniyor...")

def iade_tamamla():
    """İade işlemini bitirir"""
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor
    global barkod_lojik, agirlik_lojik, gecici_barkod, gecici_agirlik, gso_bekleniyor
    
    print("✅ İade tamamlandı")
    
    # Durumları sıfırla
    iade_aktif = False
    iade_gsi_bekliyor = False 
    iade_gso_bekliyor = False
    barkod_lojik = False
    agirlik_lojik = False
    gecici_barkod = None
    gecici_agirlik = None
    gso_bekleniyor = False
    
    if sensor_ref:
        sensor_ref.led_ac()
    
    print("🎯 Sistem hazır - Yeni ürün atabilirsiniz")

def gso_sonrasi_dogrulama():
    """GSO sonrası ürün doğrulaması"""
    global gecici_barkod, gecici_agirlik
    
    if not gecici_barkod:
        veri_temizle()
        return
    
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(gecici_barkod)
    
    if not urun_bilgisi:
        urun_iade_et("Ürün bulunamadı", "timer")
        veri_temizle()
        return
    
    # Ağırlık kontrolü
    if not agirlik_kontrol(urun_bilgisi, gecici_agirlik):
        urun_iade_et("Ağırlık uyumsuz", "gsi_bekle")
        veri_temizle()
        return
    
    # Ürün kabul edildi
    materyal_id = urun_bilgisi.get('material')
    urun_kabul_et(gecici_barkod, gecici_agirlik, materyal_id)
    
    # Konveyörü ilerlet
    if motor_ref:
        motor_ref.konveyor_ileri()
        print("▶️ Konveyör ilerliyor")
    
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
        print("❌ Kuyrukta ürün yok")
        return
    
    # En eski ürünü al
    urun = kabul_edilen_urunler.popleft()
    materyal_id = urun.get('materyal_id')
    
    print(f"🔄 Yönlendirme: {urun['barkod']} | Kalan: {len(kabul_edilen_urunler)}")
    
    if motor_ref:
        if materyal_id == 2:  # Cam
            motor_ref.yonlendirici_cam()
            print("🟦 Cam yönlendiricisi")
        else:  # Plastik/Metal
            motor_ref.yonlendirici_plastik() 
            print("🟩 Plastik yönlendiricisi")
    
    # Temizle
    yonlendirici_giris_aktif = False
    gecici_urun_uzunlugu = None

# Ana olay işleyici
def olayi_isle(olay):
    global gso_bekleniyor, yonlendirici_giris_aktif
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor
    
    print(f"📨 Olay: {olay}")
    
    # İade işlemi aktifse
    if iade_aktif:
        if olay.strip().lower() == "gsi" and iade_gsi_bekliyor:
            print("✅ İade GSI - 0.2s daha geri")
            iade_gsi_bekliyor = False
            import threading
            def ekstra_geri():
                time.sleep(0.2)
                if motor_ref and iade_aktif:
                    motor_ref.konveyor_dur()
                    global iade_gso_bekliyor
                    iade_gso_bekliyor = True
                    print("⏹️ İade durdu - GSO bekliyor")
            threading.Thread(target=ekstra_geri, daemon=True).start()
            return
            
        elif olay.strip().lower() == "gso" and iade_gso_bekliyor:
            print("✅ İade GSO - Ürün alındı")
            iade_tamamla()
            return
        else:
            print(f"⏳ İade aktif - {olay} görmezden gelindi")
            return
    
    # Normal işlemler
    olay = olay.strip().lower()
    
    if olay == "oturum_var":
        if sensor_ref:
            sensor_ref.led_ac()
    
    elif olay.startswith("a:"):
        agirlik = float(olay.split(":")[1].replace(",", "."))
        agirlik_verisi_al(agirlik)
    
    elif olay.startswith("m:"):
        uzunluk_str = olay.split(":")[1]
        uzunluk_verisi_al(uzunluk_str)
    
    elif olay == "gsi":
        if motor_ref:
            motor_ref.konveyor_ileri()
            print("▶️ GSI - Konveyör başladı")
    
    elif olay == "ysi":
        yonlendirici_giris_aktif = True
        print("🔄 YSI - Yönlendiriciye giriş")
    
    elif olay == "yso":
        print("✅ YSO - Yönlendiriciye tamamen girdi")
        if gecici_urun_uzunlugu is not None:
            yonlendirici_karar_ver()
        else:
            print("⏳ Uzunluk bekleniyor...")
    
    elif olay == "gso":
        print("🛑 GSO - Giriş kontrolü")
        if not barkod_lojik:
            urun_iade_et("Barkod yok", "timer")
            veri_temizle()
        else:
            gso_bekleniyor = True
            print("⏳ Güncel ağırlık bekleniyor...")

# Eski fonksiyon isimleri için uyumluluk
test_sistem_durumu = durum_raporu
sistem_durumunu_sifirla = sistem_sifirla