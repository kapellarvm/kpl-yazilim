import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
import threading

# Referanslar
motor_ref = None
sensor_ref = None

# Ürün verileri
agirlik = None
gecici_barkod = None
gecici_urun_uzunlugu = None

# Durum kontrolü
agirlik_lojik = False
yonlendirici_giris_aktif = False

# İade durumu
giris_iade_lojik = False
iade_aktif = False
iade_gsi_bekliyor = False
iade_gso_bekliyor = False
mesaj = None
# Kabul edilen ürünler kuyruğu
kabul_edilen_urunler = deque()
barkod_lojik_kuyruk = deque()
goruntu_lojik_kuyruk = deque()
def motor_referansini_ayarla(motor):
    global motor_ref
    motor_ref = motor
    motor_ref.motorlari_aktif_et()
    motor_ref.konveyor_dur()
    motor_ref.yonlendirici_sensor_teach()
    print("✅ Motor hazır - Sistem başlatıldı")

def sensor_referansini_ayarla(sensor):
    global sensor_ref
    sensor_ref = sensor

def barkod_verisi_al(barcode):
    global gecici_barkod, iade_aktif
    
    # İade aktifse yeni barkod işleme
    if iade_aktif:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return
    
    if barkod_lojik_kuyruk and gecici_barkod:
        print(f"🚫 [BARKOD MEVCUT] Zaten işlenen barkod var: {gecici_barkod}")
        print(f"🚫 [REDDEDİLDİ] Yeni barkod reddedildi: {barcode}")
        return

    barkod_lojik_kuyruk.append(True)
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



def gso_sonrasi_dogrulama():
    """GSO sonrası ürün doğrulaması"""
    global gecici_barkod,gecici_agirlik 

    print(f"\n🔍 [DOĞRULAMA BAŞLADI] GSO sonrası kontrol")
    
    if not gecici_barkod:
        print(f"❌ [DOĞRULAMA] Barkod verisi yok")

        return
    
    urun_bilgisi = veritabani_yoneticisi.barkodu_dogrula(gecici_barkod)
    
    if not urun_bilgisi:
        print(f"❌ [DOĞRULAMA] Veritabanında ürün bulunamadı")
        giris_iade_et("Ürün bulunamadı")

        return
    
    # Ağırlık kontrolü
    print(f"⚖️ [DOĞRULAMA] Ağırlık kontrolü yapılıyor...")
    if not agirlik_kontrol(urun_bilgisi, gecici_agirlik):
        print(f"❌ [DOĞRULAMA] Ağırlık tolerans dışında")
        giris_iade_et("Ağırlık uyumsuz")
        return
    
    # Ürün kabul edildi
    materyal_id = urun_bilgisi.get('material')
    print(f"✅ [DOĞRULAMA] Tüm kontroller başarılı")
    urun_kabul_et(gecici_barkod, gecici_agirlik, materyal_id)
    lojik_sifirla()
    

    
 
def yonlendirici_hareket():

    if not kabul_edilen_urunler:
        motor_ref.konveyor_dur()
        print("❌ [YÖNLENDİRİCİ] Kuyrukta ürün yok")
        giris_iade_et("Kuyrukta ürün yok")
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


def giris_iade_et(sebep):
    global giris_iade_lojik

    print(f"\n❌ [GİRİŞ İADESİ] Sebep: {sebep}")

    giris_iade_lojik = True
    motor_ref.konveyor_geri()

def lojik_sifirla():
    global giris_iade_lojik,gecici_barkod,gecici_agirlik

    giris_iade_lojik = False
    barkod_lojik_kuyruk.popleft() if barkod_lojik_kuyruk else None
    goruntu_lojik_kuyruk.popleft() if goruntu_lojik_kuyruk else None
    gecici_barkod = None
    gecici_agirlik = None

def agirlik_veri_kontrol(agirlik):
    global gecici_agirlik, agirlik_lojik

    gecici_agirlik = agirlik
    agirlik_lojik = True
    print(f"⚖️ [AĞIRLIK] Ağırlık verisi alındı: {agirlik} gr")

    gso_sonrasi_dogrulama()

def goruntu_isleme_tetikle():
    print("📸 [GÖRÜNTÜ İŞLEME] Görüntü işleme tetiklendi (simülasyon)")
    # Burada gerçek görüntü işleme kodu olacak
    time.sleep(0.3)  # Simülasyon için bekle
    goruntu_lojik_kuyruk.append(True)

# Ana mesaj işleyici
def mesaj_isle(mesaj):
    global yonlendirici_giris_aktif, giris_iade_lojik
    global iade_aktif, iade_gsi_bekliyor, iade_gso_bekliyor , gecici_urun_uzunlugu,agirlik 

    print(f"\n📨 [Gelen mesaj] {mesaj}")

    mesaj = mesaj.strip().lower()
    
    if mesaj == "oturum_var":
        print(f"🟢 [OTURUM] Aktif oturum başlatıldı")
        if sensor_ref:
            sensor_ref.led_ac()
            sensor_ref.teach()
    
    if mesaj.startswith("a:"):
        if barkod_lojik_kuyruk:
            agirlik = float(mesaj.split(":")[1].replace(",", "."))
            agirlik_veri_kontrol(agirlik)
        else:
            print(f"❌ [AĞIRLIK] Barkod gelmeden ağırlık verisi alındı: {mesaj}")
    
    if mesaj == "gsi":
        if not giris_iade_lojik:
            print(f"� [GSI] Şişe Geldi.")
            motor_ref.konveyor_ileri()
        else:
            time.sleep(0.2) # Gömülüden buraya  adım gibi bir mesaj eklenecek örneğin 10cm daha geri verip duracak.
            print(f"▶️ [GSI] LÜTFEN ŞİŞEYİ ALINIZ.")
            motor_ref.konveyor_dur()
    
    if mesaj == "gso":
        if not giris_iade_lojik:
            print(f"🟠 [GSO] Şişe içeride kontrole hazır.")

            if barkod_lojik_kuyruk:

                goruntu_isleme_tetikle()
                print(f"⏳ [KONTROL] Kontrol Mekanizması")

            else:

                print(f"❌ [KONTROL] Barkod verisi yok")
                giris_iade_et("Barkod yok")

                

        else :
            print(f"🟠 [GSO] İade Şişe alındı.")
            lojik_sifirla()
            


    #if mesaj == "ysi":
    #    print(f"� [YSI] Yönlendirici giriş sensörü tetiklendi")
    
    if mesaj == "yso":
        yonlendirici_hareket()

    #if mesaj.startswith("m:"):
    #    uzunluk_str = mesaj.split(":")[1]
    #    gecici_urun_uzunlugu = float(uzunluk_str.replace(",", "."))
    #    print(f"📏 [UZUNLUK] Ürün uzunluğu alındı: {gecici_urun_uzunlugu} cm")

t = threading.Thread(target=mesaj_isle, daemon=True)
t.start()