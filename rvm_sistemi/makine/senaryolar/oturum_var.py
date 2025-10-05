import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
import threading
from ..goruntu.image_processing_service import ImageProcessingService
from ..uyari_yoneticisi import uyari_yoneticisi
import asyncio
import uuid as uuid_lib
from dataclasses import dataclass, field


@dataclass
class SistemDurumu:
    # Referanslar
    motor_ref: object = None
    sensor_ref: object = None

    # Veriler
    agirlik: float = None
    uzunluk_motor_verisi: float = None

    # Listeler
    veri_senkronizasyon_listesi: list = field(default_factory=list)
    kabul_edilen_urunler: deque = field(default_factory=deque)
    
    # Lojikler
    iade_etildi: bool = False
    iade_lojik: bool = False
    iade_lojik_onceki_durum: bool = False
    barkod_lojik: bool = False
    gsi_lojik: bool = False
    gsi_gecis_lojik: bool = False
    gso_lojik: bool = False
    ysi_lojik: bool = False
    yso_lojik: bool = False

    # Alarmlar
    konveyor_alarm: bool = False
    yonlendirici_alarm: bool = False
    seperator_alarm: bool = False

    # Konumlar
    konveyor_konumda: bool = False
    yonlendirici_konumda: bool = False
    seperator_konumda: bool = False

    # Hatalar
    konveyor_hata: bool = False
    yonlendirici_hata: bool = False
    seperator_hata: bool = False

    # Kalibrasyonlar
    yonlendirici_kalibrasyon: bool = False
    seperator_kalibrasyon: bool = False

    aktif_oturum: dict = field(default_factory=lambda: {
        "aktif": False,
        "sessionId": None,
        "userId": None,
        "paket_uuid_map": {}
    })
    
# 🌍 Tekil (global) sistem nesnesi
sistem = SistemDurumu()


image_processing_service = ImageProcessingService()




def oturum_baslat(session_id, user_id):

    """DİM-DB'den gelen oturum başlatma"""
    sistem.aktif_oturum = {
        "aktif": True,
        "sessionId": session_id,
        "userId": user_id,
        "paket_uuid_map": {}
    }
    
    # Eski ürünleri temizle
    
    print(f"✅ [OTURUM] DİM-DB oturumu başlatıldı: {session_id}, Kullanıcı: {user_id}")

async def oturum_sonlandir():
    """Oturumu sonlandır ve DİM-DB'ye transaction result gönder"""
    sistem.sensor_ref.tare()
    if not sistem.aktif_oturum["aktif"]:
        print("⚠️ [OTURUM] Aktif oturum yok, sonlandırma yapılmadı")
        return

    print(f"🔚 [OTURUM] Oturum sonlandırılıyor: {sistem.aktif_oturum['sessionId']}")
    
    # DİM-DB'ye transaction result gönder
    try:
        from ...dimdb import istemci
        
        # Kabul edilen ürünleri konteyner formatına dönüştür
        containers = {}
        for urun in sistem.kabul_edilen_urunler:
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
            "containerCount": len(sistem.kabul_edilen_urunler),
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
    
    sistem.kabul_edilen_urunler.clear()
    print(f"🧹 [OTURUM] Yerel oturum temizlendi")
    
def motor_referansini_ayarla(motor):
    sistem.motor_ref = motor
    sistem.motor_ref.yonlendirici_sensor_teach()
    print("✅ Motor hazır - Sistem başlatıldı")

def sensor_referansini_ayarla(sensor):
    sistem.sensor_ref = sensor
    sistem.sensor_ref.teach()

def barkod_verisi_al(barcode):
    
    # İade aktifse yeni barkod işleme
    if sistem.iade_lojik:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return

    if sistem.barkod_lojik:
        print(f"⚠️ [BARKOD] Önceki barkod işlemesi tamamlanmadı, yeni barkod görmezden gelindi: {barcode}")
        return

    # Her barkod için benzersiz UUID oluştur
    paket_uuid = str(uuid_lib.uuid4())
    sistem.aktif_oturum["paket_uuid_map"][barcode] = paket_uuid

    sistem.barkod_lojik = True
    
    #veri_senkronizasyonu(barkod=barcode)

    veri_senkronizasyonu(barkod=barcode)
    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}, UUID: {paket_uuid}")

def goruntu_isleme_tetikle():
    goruntu_sonuc = image_processing_service.capture_and_process()
    print(f"\n📷 [GÖRÜNTÜ İŞLEME] Sonuç: {goruntu_sonuc}")
    veri_senkronizasyonu(materyal_turu=goruntu_sonuc.type.value, uzunluk=float(goruntu_sonuc.height_mm), genislik=float(goruntu_sonuc.width_mm))

def veri_senkronizasyonu(barkod=None, agirlik=None, materyal_turu=None, uzunluk=None, genislik=None):
    # Eğer kuyruk boşsa, yeni ürün başlat
    if not sistem.veri_senkronizasyon_listesi:
        sistem.veri_senkronizasyon_listesi.append({
            'barkod': None,
            'agirlik': None,
            'materyal_turu': None,
            'uzunluk': None,
            'genislik': None
        })

    # Her zaman FIFO mantığında en öndeki ürünü güncelle
    urun = sistem.veri_senkronizasyon_listesi[0]

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

    if urun['barkod'] is None and any(urun[k] is not None for k in ['agirlik', 'materyal_turu', 'uzunluk', 'genislik']):
        print(f"❌ [VERİ SENKRONİZASYONU] Karşılaştırma hatası - barkod olmadan veri geldi: {urun}")
        
        # Barkodsuz ürün için iade işlemini başlat
        sistem.iade_lojik = True

        sistem.veri_senkronizasyon_listesi.pop(0)  # hatalı ürünü sil
        print(f"🔄 [VERİ SENKRONİZASYONU] Güncel kuyruk durumu: {sistem.veri_senkronizasyon_listesi}")
        return  # çıkış yap

    if all(urun[k] is not None for k in urun):
        print(f"✅ [VERİ SENKRONİZASYONU] Tüm veriler alındı: {urun}")

        if urun['materyal_turu'] == 1:
            sistem.motor_ref.klape_plastik()

        elif urun['materyal_turu']  == 3:
            sistem.motor_ref.klape_metal()

        dogrulama(urun['barkod'], urun['agirlik'], urun['materyal_turu'], urun['uzunluk'], urun['genislik'])  

        sistem.barkod_lojik = False
        sistem.veri_senkronizasyon_listesi.pop(0)  # işlenen ürünü kuyruktan çıkar
    print(f"🔄 [VERİ SENKRONİZASYONU] Güncel kuyruk durumu: {sistem.veri_senkronizasyon_listesi}")

def dogrulama(barkod, agirlik, materyal_turu, uzunluk, genislik):

    print(f"\n📊 [DOĞRULAMA] Mevcut durum: barkod={barkod}, ağırlık={agirlik}, materyal türü={materyal_turu}, uzunluk={uzunluk}, genişlik={genislik}")

    urun = veritabani_yoneticisi.barkodu_dogrula(barkod)
    
    if not urun:
        print(f"❌ [DOĞRULAMA] Ürün veritabanında bulunamadı: {barkod}")
        dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 1, "Ürün veritabanında yok")
        sistem.iade_lojik = True
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
        #dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 2, "Ağırlık sınırları dışında")
        sistem.iade_lojik = True
        return

    if min_genislik-100 <= genislik <= max_genislik+100:
        print(f"✅ [DOĞRULAMA] Genişlik kontrolü geçti: {genislik} mm")
    else:
        print(f"❌ [DOĞRULAMA] Genişlik sınırları dışında: {genislik} mm")
        #dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 3, "Genişlik sınırları dışında")
        sistem.iade_lojik = True
        return

    if min_uzunluk-100 <= uzunluk <= max_uzunluk+100 :
        print(f"✅ [DOĞRULAMA] Uzunluk kontrolü geçti: {uzunluk} mm")
    else:
        print(f"❌ [DOĞRULAMA] Uzunluk sınırları dışında: {uzunluk} mm")
        #dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 4, "Uzunluk sınırları dışında")
        sistem.iade_lojik = True
        return

    if materyal_id != materyal_turu:
        print(f"❌ [DOĞRULAMA] Materyal türü uyuşmuyor: beklenen {materyal_id}, gelen {materyal_turu}")
        #dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 5, "Materyal türü uyuşmuyor")
        sistem.iade_lojik = True
        return
    
    print(f"✅ [DOĞRULAMA] Materyal türü kontrolü geçti: {materyal_turu}")

    # Tüm kontroller geçti, ürünü kabul et
    sistem.kabul_edilen_urunler.append({
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_turu': materyal_turu,
        'uzunluk': uzunluk,
        'genislik': genislik,
    })

    print(f"✅ [DOĞRULAMA] Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    print(f"📦 [KUYRUK] Toplam kabul edilen ürün sayısı: {len(sistem.kabul_edilen_urunler)}")

    # DİM-DB'ye kabul bildirimi gönder
    #dimdb_bildirimi_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, True, 0, "Ambalaj Kabul Edildi")

def yonlendirici_hareket():

    # Kuyruk boş mu kontrol et
    if not sistem.kabul_edilen_urunler:
        print(f"⚠️ [YÖNLENDİRME] Kabul edilen ürün kuyruğu boş, yönlendirme yapılamadı")
        return
    
    # En eski ürünü al
    urun = sistem.kabul_edilen_urunler[0]
    materyal_id = urun.get('materyal_turu')  # ✅ Düzeltildi: materyal_turu kullanılmalı
    
    materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
    materyal_adi = materyal_isimleri.get(materyal_id, "BİLİNMEYEN")
    
    print(f"\n🔄 [YÖNLENDİRME] {materyal_adi} ürün işleniyor: {urun['barkod']}")
    

    if sistem.motor_ref:
        if materyal_id == 2:  # Cam
            sistem.motor_ref.konveyor_dur()
            sistem.motor_ref.yonlendirici_cam()
            print(f"🟦 [CAM] Cam yönlendiricisine gönderildi")
        else:  # Plastik/Metal
            sistem.motor_ref.konveyor_dur()
            sistem.motor_ref.yonlendirici_plastik()
            print(f"🟩 [PLASTİK] Plastik yönlendiricisine gönderildi")
    sistem.kabul_edilen_urunler.popleft()
    print(f"📦 [KUYRUK] Kalan ürün sayısı: {len(sistem.kabul_edilen_urunler)}")
    print(f"✅ [YÖNLENDİRME] İşlem tamamlandı\n")


def lojik_yoneticisi():
    while True:

        if sistem.gsi_lojik:
            sistem.gsi_lojik = False
            sistem.gsi_gecis_lojik = True
            
            if sistem.iade_lojik:
                print("🚫 [İADE AKTIF] Şişeyi Alınız.")
                time.sleep(0.25)
                sistem.motor_ref.konveyor_dur()
            else:
                print("🔄 [LOJİK] GSI lojik işlemleri başlatıldı")
                sistem.motor_ref.konveyor_ileri()
        
        if sistem.gso_lojik:
            sistem.gso_lojik = False
            if sistem.iade_lojik:
                print("Ürünü aldı. Sistem Tekrar Aktif Teşekkürler.")
                sistem.iade_lojik = False
                sistem.barkod_lojik = False
            else:
                if sistem.barkod_lojik:
                    if sistem.iade_lojik==False:
                        print("[GSO] Sistem Normal Çalışıyor. Görüntü İşleme Başlatılıyor.")
                        goruntu_isleme_tetikle()
                    else:
                        print("🚫 [İADE AKTIF] Görüntü İşleme Başlatılamıyor.")
                else:
                    print("🚫 [GSO] Barkod okunmadı, ürünü iade et.")
                    sistem.iade_lojik = True

        if sistem.yso_lojik:
            sistem.yso_lojik = False
            print("🔄 [LOJİK] YSO lojik işlemleri başlatıldı")
            yonlendirici_hareket()

        if sistem.yonlendirici_konumda:
            sistem.yonlendirici_konumda = False
            if len(sistem.veri_senkronizasyon_listesi)>0 or len(sistem.kabul_edilen_urunler)>0:
                print("🔄 [LOJİK] Yönlendirici konumda, konveyör ileri")
                sistem.motor_ref.konveyor_ileri()
            else:
                if sistem.gsi_gecis_lojik and not sistem.iade_lojik:
                    print("✅ [LOJİK] Yönlendirici konumda, konveyör ileri gsi_gecis_lojik aktif")
                    sistem.motor_ref.konveyor_ileri()
                    sistem.gsi_gecis_lojik = False

                else:
                    print("✅ [LOJİK] Yönlendirici konumda, konveyör dur")
                    time.sleep(0.25) # Gömülüden adım gibi bişe girecem.
                    sistem.motor_ref.konveyor_dur()
                    


        if sistem.agirlik is not None:
            if sistem.barkod_lojik:
                if sistem.iade_lojik==False:
                    print(f"⚖️ [AĞIRLIK] Ölçülen ağırlık: {sistem.agirlik} gr")
                    veri_senkronizasyonu(agirlik=sistem.agirlik)
                    sistem.agirlik = None  # Sıfırla
                else:
                    print(f"🚫 [İADE AKTIF] Ağırlık ölçümü iade lojik aktifken işlenmiyor: {sistem.agirlik} gr")
                    sistem.agirlik = None  # Sıfırla
            else:
                print(f"⚠️ [AĞIRLIK] Ölçülen ağırlık var ama barkod lojik aktif değil: {sistem.agirlik} gr")
                sistem.agirlik = None  # Sıfırla

        # İade lojik flag mantığı - false'dan true'ya geçtiğinde bir kez çalışır
        if sistem.iade_lojik:
            if len(sistem.kabul_edilen_urunler) == 0 and len(sistem.veri_senkronizasyon_listesi) == 0:
                if not sistem.iade_etildi:
                    print("🚫 [İADE] İade lojik aktif, ürün iade ediliyor...")
                    giris_iade_et("Kabul edilen ürün yok")
                    sistem.iade_etildi = True
        else:
            # iade_lojik kapandığında tekrar aktifleşmeye izin ver
            sistem.iade_etildi = False
     

def giris_iade_et(sebep):
    print(f"\n❌ [GİRİŞ İADESİ] Sebep: {sebep}")
    sistem.motor_ref.konveyor_geri()

def mesaj_isle(mesaj):

    mesaj = mesaj.strip().lower()
    
    if mesaj == "oturum_var":
        print(f"🟢 [OTURUM] Aktif oturum başlatıldı")
        t1 = threading.Thread(target=lojik_yoneticisi, daemon=True)
        t2 = threading.Thread(target=goruntu_isleme_tetikle, daemon=True)

        t1.start()
        t2.start()

        sistem.iade_lojik = False
        sistem.iade_lojik_onceki_durum = False
        sistem.barkod_lojik = False
        sistem.veri_senkronizasyon_listesi.clear()
        sistem.kabul_edilen_urunler.clear()

        sistem.motor_ref.motorlari_aktif_et()
        sistem.sensor_ref.tare()
        sistem.motor_ref.konveyor_dur()
        sistem.sensor_ref.led_ac()
        sistem.sensor_ref.doluluk_oranı()

    if mesaj.startswith("a:"):
        sistem.agirlik = float(mesaj.split(":")[1].replace(",", "."))
    if mesaj == "gsi":
        sistem.gsi_lojik = True
    if mesaj == "gso":
        sistem.gso_lojik = True
    if mesaj == "yso":
        sistem.yso_lojik = True
    if mesaj == "ysi":
        sistem.ysi_lojik = True
    if mesaj.startswith("m:"):
        sistem.uzunluk_motor_verisi = float(mesaj.split(":")[1].replace(",", "."))
    if mesaj == "kma":
        sistem.konveyor_alarm = True
    if mesaj == "yma":
        sistem.yonlendirici_alarm = True
    if mesaj == "sma":
        sistem.seperator_alarm = True
    if mesaj == "kmk":
        sistem.konveyor_konumda = True
    if mesaj == "ymk":
        sistem.yonlendirici_konumda = True
    if mesaj == "smk":  
        sistem.seperator_konumda = True
    if mesaj == "kmh":
        sistem.konveyor_hata = True
    if mesaj == "ymh":  
        sistem.yonlendirici_hata = True
    if mesaj == "smh":  
        sistem.seperator_hata = True
    if mesaj == "ykt":
        sistem.yonlendirici_kalibrasyon = True
    if mesaj == "skt":  
        sistem.seperator_kalibrasyon = True





# Erikli barkod: 1923026353360
# Erikli büyük barkod: 1923026353391
# Kuzeyden barkod: 19270737
# Nestle barkod: 1923026353469
# Damla barkod: 8333445997848

# kPONVEYÖR İLERİ VE GERİ DÖNERKEN TAM TUR DÖNÜNCE BURAYA KOMUT ATSIN. BİRDE GÖMÜLÜ YAZIIMDA 
# EĞER O ARADA YMP,YMC GİBİ MOUTLAR GİDERSE O DURUMU SIFIRLASINKİ HER TAM TURDA KOMUT ATMASIN EKSTREM
# DURUMLARDA SADECE KOMUT ATSIN