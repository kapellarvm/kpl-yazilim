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
veri_senkronizasyonu_kuyrugu = deque()

barkod_lojik = False

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
    global giris_iade_lojik, barkod_lojik
    
    # İade aktifse yeni barkod işleme
    if giris_iade_lojik:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return

    
    barkod_lojik = True
    veri_senkronizasyonu(barkod=barcode)

    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}")   


def dogrulama(barkod, agirlik, materyal_turu, uzunluk, genislik):
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
    min_genislik = urun.get('packMinWidth')
    max_genislik = urun.get('packMaxWidth')
    min_uzunluk = urun.get('packMinHeight')
    max_uzunluk = urun.get('packMaxHeight')
    

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

    if uzunluk is not None and (uzunluk < min_uzunluk or uzunluk > max_uzunluk):
        print(f"❌ [DOĞRULAMA] Uzunluk sınırları dışında: {uzunluk} cm (Beklenen: {min_uzunluk}-{max_uzunluk} cm)")
        giris_iade_et("Uzunluk sınırları dışında")
        return
    
    if genislik is not None and (genislik < min_genislik or genislik > max_genislik):
        print(f"❌ [DOĞRULAMA] Genişlik sınırları dışında: {genislik} cm (Beklenen: {min_genislik}-{max_genislik} cm)")
        giris_iade_et("Genişlik sınırları dışında")
        return
    
    if materyal_turu:
        materyal_turu = materyal_turu.lower()
        if materyal_id == 1 and materyal_turu != "plastik":
            print(f"❌ [DOĞRULAMA] Materyal türü uyuşmuyor: Beklenen Plastik, Gelen {materyal_turu}")
            giris_iade_et("Materyal türü uyuşmuyor")
            return
        elif materyal_id == 2 and materyal_turu != "cam":
            print(f"❌ [DOĞRULAMA] Materyal türü uyuşmuyor: Beklenen Cam, Gelen {materyal_turu}")
            giris_iade_et("Materyal türü uyuşmuyor")
            return
        elif materyal_id == 3 and materyal_turu not in ["metal", "alu", "alüminyum", "aluminyum", "alüminyum"]:
            print(f"❌ [DOĞRULAMA] Materyal türü uyuşmuyor: Beklenen Metal, Gelen {materyal_turu}")
            giris_iade_et("Materyal türü uyuşmuyor")
            return
        else:
            print(f"📊 [DOĞRULAMA] Materyal türü kontrolü geçti: {materyal_turu}")
    else:
        print(f"❌ [DOĞRULAMA] Materyal türü bilgisi yok")
        giris_iade_et("Materyal türü bilgisi yok")
        return
    # Tüm kontroller geçti, ürünü kabul et
    kabul_edilen_urunler.append({
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_turu': materyal_turu
    })

    print(f"✅ [DOĞRULAMA] Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    print(f"📦 [KUYRUK] Toplam kabul edilen ürün sayısı: {len(kabul_edilen_urunler)}")

def yonlendirici_hareket():


    
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
    global giris_iade_lojik, barkod_lojik
    giris_iade_lojik = False
    barkod_lojik = False

def goruntu_isleme_tetikle():
    print("📸 [GÖRÜNTÜ İŞLEME] Görüntü işleme tetiklendi (simülasyon)")
    # Burada gerçek görüntü işleme kodu olacak
    time.sleep(0.3)  # Simülasyon için bekle
    goruntu_sonuc = ["plastik", 103.55, 58.5]
    veri_senkronizasyonu(materyal_turu=goruntu_sonuc[0], uzunluk=goruntu_sonuc[1], genislik=goruntu_sonuc[2])


def veri_senkronizasyonu(barkod=None, agirlik=None, materyal_turu=None, uzunluk=None, genislik=None):
    global barkod_lojik
    # Eğer kuyruk boşsa, yeni ürün başlat
    if not veri_senkronizasyonu_kuyrugu:
        veri_senkronizasyonu_kuyrugu.append({
            'barkod': None,
            'agirlik': None,
            'materyal_turu': None,
            'uzunluk': None,
            'genislik': None
        })

    # Her zaman FIFO mantığında en öndeki ürünü güncelle
    urun = veri_senkronizasyonu_kuyrugu[0]

    if barkod is not None:
        urun['barkod'] = barkod
    if agirlik is not None:
        urun['agirlik'] = agirlik
    if materyal_turu is not None:
        urun['materyal_turu'] = materyal_turu
    if uzunluk is not None:
        urun['uzunluk'] = uzunluk
    if genislik is not None:
        urun['genislik'] = genislik

    # Eğer tüm alanlar dolduysa ürünü işleme al
    print(f"🔍 [VERİ SENKRONİZASYONU] Güncel ürün durumu: {urun}")

    if urun['barkod'] is None and any(urun[k] is not None for k in ['agirlik', 'materyal_turu', 'uzunluk', 'genislik']):
        print(f"❌ [VERİ SENKRONİZASYONU] Karşılaştırma hatası - barkod olmadan veri geldi: {urun}")
    
        veri_senkronizasyonu_kuyrugu.popleft()  # hatalı ürünü sil
        print(f"🔄 [VERİ SENKRONİZASYONU] Güncel kuyruk durumu: {veri_senkronizasyonu_kuyrugu}")
        return  # çıkış yap

    if all(urun[k] is not None for k in urun):
        print(f"✅ [VERİ SENKRONİZASYONU] Tüm veriler alındı: {urun}")
        dogrulama(urun['barkod'], urun['agirlik'], urun['materyal_turu'], urun['uzunluk'], urun['genislik'])
        veri_senkronizasyonu_kuyrugu.popleft()  # işlenen ürünü kuyruktan çıkar
    print(f"🔄 [VERİ SENKRONİZASYONU] Güncel kuyruk durumu: {veri_senkronizasyonu_kuyrugu}")



def mesaj_isle(mesaj):
    global giris_iade_lojik, agirlik, barkod_lojik

    mesaj = mesaj.strip().lower()
    
    if mesaj == "oturum_var":
        print(f"🟢 [OTURUM] Aktif oturum başlatıldı")
        if sensor_ref:
            sensor_ref.led_ac()
            lojik_sifirla()
    
    if mesaj.startswith("a:"):
        if not giris_iade_lojik:
            agirlik = float(mesaj.split(":")[1].replace(",", "."))
            veri_senkronizasyonu(agirlik=agirlik)
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

            if barkod_lojik:
                goruntu_isleme_tetikle()

            else:
                print(f"❌ [KONTROL] Barkod verisi yok")
                giris_iade_et("Barkod yok")          

        else :
            print(f"🟠 [GSO] İade Şişe alındı.")
            time.sleep(2)
            lojik_sifirla()
    
    if mesaj == "yso":
        print(f"🔵 [YSO] Yönlendirici sensör tetiklendi.")
        yonlendirici_hareket()



t1 = threading.Thread(target=veri_senkronizasyonu, daemon=True)
t2 = threading.Thread(target=mesaj_isle, daemon=True)
t1.start()
t2.start()

# Erikli barkod: 1923026353360
# Erikli büyük barkod: 1923026353391
# Kuzeyden barkod: 19270737
# Nestle barkod: 1923026353469
# Damla barkod: 8333445997848