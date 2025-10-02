import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
import threading

# Referanslar
motor_ref = None
sensor_ref = None

# Ürün verileri
agirlik = None
# İade durumu
giris_iade_lojik = False
mesaj = None

# Kabul edilen ürünler kuyruğu
kabul_edilen_urunler = deque()

agirlik_kuyruk = deque()
barkod_kuyruk = deque()
goruntu_kuyruk = deque()



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
    sensor_ref.teach()

def barkod_verisi_al(barcode):
    global giris_iade_lojik
    
    # İade aktifse yeni barkod işleme
    if giris_iade_lojik:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return

    if barkod_kuyruk:
        print(f"🚫 [BARKOD MEVCUT] Zaten işlenen barkod var: {barkod_kuyruk[0]}")
        print(f"🚫 [REDDEDİLDİ] Yeni barkod reddedildi: {barcode}")
        return
    
    barkod_kuyruk.append(barcode)
    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}")   

def kuyruk_dogrulama():
    print("Barkod Kuyruk:" + str(len(barkod_kuyruk)) + " Ağırlık Kuyruk:" + str(len(agirlik_kuyruk)) + " Görüntü Kuyruk:" + str(len(goruntu_kuyruk)))
    if not barkod_kuyruk:
        print(f"❌ [KUYRUK DOĞRULAMA] Barkod verisi yok")
        lojik_sifirla()
        giris_iade_et("Barkod yok")
        return
    
    if not agirlik_kuyruk:
        print(f"❌ [KUYRUK DOĞRULAMA] Ağırlık verisi yok")
        lojik_sifirla()
        giris_iade_et("Ağırlık yok")
        return
    
    if not goruntu_kuyruk:
        print(f"❌ [KUYRUK DOĞRULAMA] Görüntü işleme verisi yok")
        lojik_sifirla()
        giris_iade_et("Görüntü yok")
        return

    if len(barkod_kuyruk) == len(agirlik_kuyruk) == len(goruntu_kuyruk):
        print(f"✅ [KUYRUK DOĞRULAMA] Kuyruk uzunlukları eşit")
   
        barkod = barkod_kuyruk.popleft()
        agirlik = agirlik_kuyruk.popleft()
        materyal_tipi, uzunluk, genislik = goruntu_kuyruk.popleft()

        print(f"\n🔄 [KUYRUK DOĞRULAMA] Veriler alındı: barkod={barkod}, ağırlık={agirlik}, materyal={materyal_tipi}, uzunluk={uzunluk}, genişlik={genislik}")

        dogrulama(barkod, agirlik, materyal_tipi, uzunluk, genislik)

    else:
        giris_iade_et("Kuyruk uzunlukları eşit değil")
        print(f"❌ [KUYRUK DOĞRULAMA] Kuyruk uzunlukları eşit değil: barkod={len(barkod_kuyruk)}, ağırlık={len(agirlik_kuyruk)}, görüntü={len(goruntu_kuyruk)}")

def dogrulama(barkod, agirlik, materyal_tipi, uzunluk, genislik):
    global kabul_edilen_urunler

    print(f"\n📊 [DOĞRULAMA] Mevcut durum: barkod={barkod}, ağırlık={agirlik}")

    urun = veritabani_yoneticisi.barkodu_dogrula(barkod)
    
    if not urun:
        print(f"❌ [DOĞRULAMA] Ürün veritabanında bulunamadı: {barkod}")
        giris_iade_et("Ürün veritabanında yok")
        return

    materyal_id = urun.get('material')
    min_agirlik = urun.get('packMinWeight')
    max_agirlik = urun.get('packMaxWeight')

    print(f"📊 [DOĞRULAMA] Ölçülen ağırlık: {agirlik} gr")
    
    agirlik_kabul = False
    if min_agirlik is None and max_agirlik is None:
        agirlik_kabul = True
    elif min_agirlik is not None and max_agirlik is not None:
        agirlik_kabul = (min_agirlik-20<= agirlik <= max_agirlik+20)
    elif min_agirlik is not None:
        agirlik_kabul = (agirlik >= min_agirlik-20)
    elif max_agirlik is not None:
        agirlik_kabul = (agirlik <= max_agirlik+20)

    print(f"📊 [DOĞRULAMA] Ağırlık kontrol sonucu: {agirlik_kabul}")

    if not agirlik_kabul:
        giris_iade_et("Ağırlık sınırları dışında")
        return

    # Tüm kontroller geçti, ürünü kabul et
    kabul_edilen_urunler.append({
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_id': materyal_id
    })

    print(f"✅ [DOĞRULAMA] Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    print(f"📦 [KUYRUK] Toplam kabul edilen ürün sayısı: {len(kabul_edilen_urunler)}")

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
    
    print(f"✅ [YÖNLENDİRME] İşlem tamamlandı\n")

def giris_iade_et(sebep):
    global giris_iade_lojik

    print(f"\n❌ [GİRİŞ İADESİ] Sebep: {sebep}")

    giris_iade_lojik = True
    motor_ref.konveyor_geri()

def lojik_sifirla():
    global agirlik

    barkod_kuyruk.clear()
    goruntu_kuyruk.clear()
    agirlik_kuyruk.clear()

def goruntu_isleme_tetikle():
    print("📸 [GÖRÜNTÜ İŞLEME] Görüntü işleme tetiklendi (simülasyon)")
    # Burada gerçek görüntü işleme kodu olacak
    time.sleep(0.3)  # Simülasyon için bekle
    goruntu_sonuc = ["plastik", 103.55, 58.5]
    goruntu_kuyruk.append(goruntu_sonuc)

# Ana mesaj işleyici
def mesaj_isle(mesaj):
    global giris_iade_lojik, agirlik

    print(f"\n📨 [Gelen mesaj] {mesaj}")

    mesaj = mesaj.strip().lower()
    
    if mesaj == "oturum_var":
        print(f"🟢 [OTURUM] Aktif oturum başlatıldı")
        if sensor_ref:
            sensor_ref.led_ac()
            lojik_sifirla()
    
    if mesaj.startswith("a:"):
        if not giris_iade_lojik:
            agirlik = float(mesaj.split(":")[1].replace(",", "."))
            agirlik_kuyruk.append(agirlik)
            agirlik = None
        else:
            print(f"🚫 [İADE AKTIF] Ağırlık görmezden gelindi: {mesaj}")
    
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

            if barkod_kuyruk and agirlik_kuyruk:

                goruntu_isleme_tetikle()
                kuyruk_dogrulama()

            else:

                print(f"❌ [KONTROL] Barkod verisi yok")
                giris_iade_et("Barkod yok")

                

        else :
            print(f"🟠 [GSO] İade Şişe alındı.")
            time.sleep(2)
            giris_iade_lojik = False
            lojik_sifirla()
    
    if mesaj == "yso":
        yonlendirici_hareket()



t1 = threading.Thread(target=kuyruk_dogrulama, daemon=True)
t2 = threading.Thread(target=mesaj_isle, daemon=True)
t1.start()
t2.start()

# Erikli barkod: 1923026353360
# Erikli büyük barkod: 1923026353391
# Kuzeyden barkod: 19270737
# Nestle barkod: 1923026353469
# Damla barkod: 8333445997848