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

    # Lojikler
    iade_lojik: bool = False
    barkod_lojik: bool = False
    gsi_lojik: bool = False
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
    
    if not sistem.aktif_oturum["aktif"]:
        print("⚠️ [OTURUM] Aktif oturum yok, sonlandırma yapılmadı")
        return

    print(f"🔚 [OTURUM] Oturum sonlandırılıyor: {sistem.aktif_oturum['sessionId']}")
    
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
    
    # İade aktifse yeni barkod işleme
    if sistem.iade_lojik:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        return

    # Her barkod için benzersiz UUID oluştur
    paket_uuid = str(uuid_lib.uuid4())
    sistem.aktif_oturum["paket_uuid_map"][barcode] = paket_uuid

    sistem.barkod_lojik = True
    #veri_senkronizasyonu(barkod=barcode)

    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}, UUID: {paket_uuid}")   

def motor_referansini_ayarla(motor):
    sistem.motor_ref = motor
    sistem.motor_ref.yonlendirici_sensor_teach()
    print("✅ Motor hazır - Sistem başlatıldı")

def sensor_referansini_ayarla(sensor):
    sistem.sensor_ref = sensor
    sistem.sensor_ref.teach()



def lojik_yoneticisi():
    while True:

        if sistem.gsi_lojik:
            sistem.gsi_lojik = False
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
                    print("Sistem Normal Çalışıyor")
                else:
                    sistem.iade_lojik = True
                    sistem.motor_ref.konveyor_geri()
        
        if sistem.agirlik is not None:
            print(f"⚖️ [AĞIRLIK] Ölçülen ağırlık: {sistem.agirlik} gr")
            sistem.agirlik = None  # Sıfırla
        

def mesaj_isle(mesaj):

    mesaj = mesaj.strip().lower()
    
    if mesaj == "oturum_var":
        print(f"🟢 [OTURUM] Aktif oturum başlatıldı")
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


t1 = threading.Thread(target=lojik_yoneticisi, daemon=True)
t1.start()