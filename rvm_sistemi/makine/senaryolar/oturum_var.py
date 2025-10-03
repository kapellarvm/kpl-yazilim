import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
import threading
from ..goruntu.image_processing_service import ImageProcessingService
from ..uyari_yoneticisi import uyari_yoneticisi
import asyncio
import uuid as uuid_lib

image_processing_service = ImageProcessingService()

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

# DİM-DB Oturum bilgileri
aktif_oturum = {
    "aktif": False,
    "sessionId": None,
    "userId": None,
    "paket_uuid_map": {}  # Her paket için UUID haritalama
}

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

def oturum_baslat(session_id, user_id):
    """DİM-DB'den gelen oturum başlatma"""
    global aktif_oturum, kabul_edilen_urunler
    
    aktif_oturum = {
        "aktif": True,
        "sessionId": session_id,
        "userId": user_id,
        "paket_uuid_map": {}
    }
    
    # Eski ürünleri temizle
    kabul_edilen_urunler.clear()
    
    print(f"✅ [OTURUM] DİM-DB oturumu başlatıldı: {session_id}, Kullanıcı: {user_id}")

async def oturum_sonlandir():
    """Oturumu sonlandır ve DİM-DB'ye transaction result gönder"""
    global aktif_oturum
    
    if not aktif_oturum["aktif"]:
        print("⚠️ [OTURUM] Aktif oturum yok, sonlandırma yapılmadı")
        return
    
    print(f"🔚 [OTURUM] Oturum sonlandırılıyor: {aktif_oturum['sessionId']}")
    
    # DİM-DB'ye transaction result gönder
    try:
        from ...dimdb import istemci
        
        # Kabul edilen ürünleri konteyner formatına dönüştür
        containers = {}
        for urun in kabul_edilen_urunler:
            barcode = urun["barkod"]
            if barcode not in containers:
                containers[barcode] = {
                    "barcode": barcode,
                    "material": urun["materyal_turu"],
                    "count": 0,
                    "weight": 0
                }
            containers[barcode]["count"] += 1
            containers[barcode]["weight"] += urun["agirlik"]
        
        transaction_payload = {
            "guid": str(uuid_lib.uuid4()),
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "rvm": istemci.RVM_ID,
            "id": aktif_oturum["sessionId"] + "-tx",
            "firstBottleTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "endTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "sessionId": aktif_oturum["sessionId"],
            "userId": aktif_oturum["userId"],
            "created": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "containerCount": len(kabul_edilen_urunler),
            "containers": list(containers.values())
        }
        
        # Async fonksiyonu await ile çağır
        await istemci.send_transaction_result(transaction_payload)
        print(f"✅ [OTURUM] Transaction result DİM-DB'ye gönderildi")
        
    except Exception as e:
        print(f"❌ [OTURUM] Transaction result gönderme hatası: {e}")
    
    # Oturumu temizle
    aktif_oturum = {
        "aktif": False,
        "sessionId": None,
        "userId": None,
        "paket_uuid_map": {}
    }
    
    kabul_edilen_urunler.clear()
    print(f"🧹 [OTURUM] Yerel oturum temizlendi")

def barkod_verisi_al(barcode):
    global giris_iade_lojik, barkod_lojik, aktif_oturum
    
    # İade aktifse yeni barkod işleme
    if giris_iade_lojik:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return

    # Her barkod için benzersiz UUID oluştur
    paket_uuid = str(uuid_lib.uuid4())
    aktif_oturum["paket_uuid_map"][barcode] = paket_uuid
    
    barkod_lojik = True
    veri_senkronizasyonu(barkod=barcode)

    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}, UUID: {paket_uuid}")   


def dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji):
    """DİM-DB'ye paket kabul/red sonucunu bildirir"""
    global aktif_oturum
    
    if not aktif_oturum["aktif"]:
        print("⚠️ [DİM-DB] Aktif oturum yok, bildirim gönderilmedi")
        return
    
    try:
        from ...dimdb import istemci
        
        # UUID'yi al
        paket_uuid = aktif_oturum["paket_uuid_map"].get(barkod, str(uuid_lib.uuid4()))
        
        # Kabul edilen ürün sayılarını hesapla
        pet_sayisi = sum(1 for u in kabul_edilen_urunler if u.get('materyal_turu') == 1)
        cam_sayisi = sum(1 for u in kabul_edilen_urunler if u.get('materyal_turu') == 2)
        alu_sayisi = sum(1 for u in kabul_edilen_urunler if u.get('materyal_turu') == 3)
        
        result_payload = {
            "guid": str(uuid_lib.uuid4()),
            "uuid": paket_uuid,
            "sessionId": aktif_oturum["sessionId"],
            "barcode": barkod,
            "measuredPackWeight": float(agirlik),
            "measuredPackHeight": float(uzunluk),
            "measuredPackWidth": float(genislik),
            "binId": materyal_turu if kabul_edildi else -1,
            "result": sebep_kodu,
            "resultMessage": sebep_mesaji,
            "acceptedPetCount": pet_sayisi,
            "acceptedGlassCount": cam_sayisi,
            "acceptedAluCount": alu_sayisi
        }
        
        # Yeni event loop oluşturarak async fonksiyonu çalıştır
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(istemci.send_accept_package_result(result_payload))
            print(f"✅ [DİM-DB] Accept package result gönderildi: {barkod} -> {'KABUL' if kabul_edildi else 'RED'}")
        finally:
            loop.close()
        
    except Exception as e:
        print(f"❌ [DİM-DB] Accept package result gönderme hatası: {e}")

def dogrulama(barkod, agirlik, materyal_turu, uzunluk, genislik):
    global kabul_edilen_urunler

    print(f"\n📊 [DOĞRULAMA] Mevcut durum: barkod={barkod}, ağırlık={agirlik}")

    urun = veritabani_yoneticisi.barkodu_dogrula(barkod)
    
    if not urun:
        print(f"❌ [DOĞRULAMA] Ürün veritabanında bulunamadı: {barkod}")
        dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 1, "Ürün veritabanında yok")
        giris_iade_et("Ürün veritabanında yok")
        return

    min_agirlik = urun.get('packMinWeight')
    max_agirlik = urun.get('packMaxWeight')
    min_genislik = urun.get('packMinWidth')
    max_genislik = urun.get('packMaxWidth')
    min_uzunluk = urun.get('packMinHeight')
    max_uzunluk = urun.get('packMaxHeight')
    materyal_id = urun.get('material')    

    print(f"📊 [DOĞRULAMA] Min Agirlik: {min_agirlik}, Max Agirlik: {max_agirlik}, Min Genişlik: {min_genislik}, Max Genişlik: {max_genislik}, Min Uzunluk: {min_uzunluk}, Max Uzunluk: {max_uzunluk}, Materyal_id: {materyal_id}")

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
        dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 2, "Ağırlık sınırları dışında")
        giris_iade_et("Ağırlık sınırları dışında")
        return

    if min_genislik <= genislik <= max_genislik:
        print(f"✅ [DOĞRULAMA] Genişlik kontrolü geçti: {genislik} mm")
    else:
        print(f"❌ [DOĞRULAMA] Genişlik sınırları dışında: {genislik} mm")
        dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 3, "Genişlik sınırları dışında")
        giris_iade_et("Genişlik sınırları dışında")
        return

    if min_uzunluk <= uzunluk <= max_uzunluk:
        print(f"✅ [DOĞRULAMA] Uzunluk kontrolü geçti: {uzunluk} mm")
    else:
        print(f"❌ [DOĞRULAMA] Uzunluk sınırları dışında: {uzunluk} mm")
        dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 4, "Uzunluk sınırları dışında")
        giris_iade_et("Uzunluk sınırları dışında")
        return

    if materyal_id != materyal_turu:
        print(f"❌ [DOĞRULAMA] Materyal türü uyuşmuyor: beklenen {materyal_id}, gelen {materyal_turu}")
        dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 5, "Materyal türü uyuşmuyor")
        giris_iade_et("Materyal türü uyuşmuyor")
        return
    
    print(f"✅ [DOĞRULAMA] Materyal türü kontrolü geçti: {materyal_turu}")

    # Tüm kontroller geçti, ürünü kabul et
    kabul_edilen_urunler.append({
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_turu': materyal_turu,
        'uzunluk': uzunluk,
        'genislik': genislik,
    })

    print(f"✅ [DOĞRULAMA] Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    print(f"📦 [KUYRUK] Toplam kabul edilen ürün sayısı: {len(kabul_edilen_urunler)}")
    
    # DİM-DB'ye kabul bildirimi gönder
    dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, True, 0, "Ambalaj Kabul Edildi")

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
    time.sleep(0.3)  # Görüntü işleme süresi
    goruntu_sonuc = image_processing_service.capture_and_process()
    print(f"\n📷 [GÖRÜNTÜ İŞLEME] Sonuç: {goruntu_sonuc}")
    veri_senkronizasyonu(materyal_turu=goruntu_sonuc.type.value, uzunluk=float(goruntu_sonuc.height_mm), genislik=float(goruntu_sonuc.width_mm))


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
            uyari_yoneticisi.uyari_goster("Lütfen Şişeyi Alınız", 1)
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



# Threading kaldırıldı - mesaj_isle() fonksiyonu parametre bekliyor
# Bu fonksiyonlar durum_makinesi tarafından çağrılıyor

# Erikli barkod: 1923026353360
# Erikli büyük barkod: 1923026353391
# Kuzeyden barkod: 19270737
# Nestle barkod: 1923026353469
# Damla barkod: 8333445997848

# Uyarı göstermek için direkt uyari_yoneticisi kullanın:
# uyari_yoneticisi.uyari_goster("Mesaj", 2)