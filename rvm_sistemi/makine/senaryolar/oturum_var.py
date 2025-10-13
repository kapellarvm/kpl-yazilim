import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
import threading
from ..goruntu.goruntu_isleme_servisi import GoruntuIslemeServisi
import uuid as uuid_lib
from dataclasses import dataclass, field
from . import uyari
from ...utils.logger import log_oturum_var, log_error, log_success, log_warning, log_system
from enum import Enum, auto
from datetime import datetime
from pprint import pprint

class SistemAkisDurumu(Enum):
    BEKLEMEDE = auto()
    GIRIS_ALGILANDI = auto()
    DOGRULAMA_BASLADI = auto()
    VERI_BEKLENIYOR = auto()
    YONLENDIRICI_KABUL = auto()
    YONLENDIRICI_HAREKET = auto()
    YONLENDIRICI_SAHTECILIK = auto()
    IADE_EDILIYOR = auto()


@dataclass
class SistemDurumu:

    akis_durumu: SistemAkisDurumu = SistemAkisDurumu.BEKLEMEDE
    
    
    mevcut_barkod: str = None
    mevcut_agirlik: float = None
    mevcut_materyal_turu: int = None
    mevcut_uzunluk: float = None
    mevcut_genislik: float = None
    iade_sebep: str = None

    # Referanslar
    motor_ref: object = None
    sensor_ref: object = None
    motor_kontrol_ref: object = None  # GA500 motor kontrol referansı

    # Veriler
    agirlik: float = None
    uzunluk_motor_verisi: float = None
    uzunluk_goruntu_isleme: float = None

    # Listeler
    kabul_edilen_urunler: deque = field(default_factory=deque)
    urun_listesi: list = field(default_factory=list)
    son_id : int = 0
    # İade Sebep String
    iade_sebep: str = None

    # Lojikler
    barkod_lojik: bool = False
    lojik_thread_basladi: bool = False
    gsi_lojik: bool = False
    gso_lojik: bool = False
    ysi_lojik: bool = False
    yso_lojik: bool = False
    ezici_durum : bool = False
    kirici_durum : bool = False
    
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
    konveyor_adim_problem: bool = False # Konveyör hiç durmadan bir yönde dönerse bu hata true olur

    # Kalibrasyonlar
    yonlendirici_kalibrasyon: bool = False
    seperator_kalibrasyon: bool = False


    aktif_oturum: dict = field(default_factory=lambda: {
        "aktif": False,
        "sessionId": None,
        "userId": None,
        "paket_uuid_map": {}
    })

# DİM-DB bildirim fonksiyonu - direkt import ile
def dimdb_bildirim_gonder(barcode, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji):
    """DİM-DB'ye bildirim gönderir"""
    try:
        from ...dimdb.dimdb_yoneticisi import dimdb_bildirim_gonder as sunucu_dimdb_bildirim
        sunucu_dimdb_bildirim(barcode, agirlik, materyal_turu, uzunluk, genislik, kabul_edildi, sebep_kodu, sebep_mesaji)
    except Exception as e:
        print(f"❌ [DİM-DB BİLDİRİM] Hata: {e}")
        log_error(f"DİM-DB BİLDİRİM Hata: {e}")

def motor_referansini_ayarla(motor):
    sistem.motor_ref = motor
    sistem.motor_ref.yonlendirici_sensor_teach()
    print("✅ Motor hazır - Sistem başlatıldı")
    log_oturum_var("Motor hazır - Sistem başlatıldı")

def sensor_referansini_ayarla(sensor):
    sistem.sensor_ref = sensor
    sistem.sensor_ref.teach()

def motor_kontrol_referansini_ayarla(motor_kontrol):
    """GA500 Motor Kontrol referansını ayarla"""
    sistem.motor_kontrol_ref = motor_kontrol
    print("✅ Motor kontrol referansı ayarlandı - Otomatik ezici kontrolü aktif")
    log_oturum_var("Motor kontrol referansı ayarlandı - Otomatik ezici kontrolü aktif")

def barkod_verisi_al(barcode):
    # Ürün bekleme veya giriş aşamasındayken barkodu kabul et
    if not sistem.barkod_lojik:
         sistem.mevcut_barkod = barcode
         sistem.barkod_lojik = True 
         print(f"🔗 [{barcode}] Barkod alındı.")
    else:
         print(f"⚠️ Barkod okundu ama sistem ürün kabul etmiyor. Durum: {sistem.akis_durumu}")

def goruntu_isleme_tetikle():
    """Görüntü işlemeyi tetikler ve sonuçları veri senkronizasyonuna gönderir"""
    goruntu_sonuc = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
    
    print(f"\n📷 [GÖRÜNTÜ İŞLEME] Sonuç: {goruntu_sonuc}")
    
    log_oturum_var(f"GÖRÜNTÜ İŞLEME - Sonuç: {goruntu_sonuc}")

    sistem.uzunluk_goruntu_isleme = float(goruntu_sonuc.genislik_mm)
    sistem.mevcut_materyal_turu = goruntu_sonuc.tur.value
    sistem.mevcut_uzunluk = float(goruntu_sonuc.genislik_mm)
    sistem.mevcut_genislik = float(goruntu_sonuc.yukseklik_mm)

def dogrulama(barkod, agirlik, materyal_turu, uzunluk, genislik):

    print(f"\n📊 [DOĞRULAMA] Mevcut durum: barkod={barkod}, ağırlık={agirlik}, materyal türü={materyal_turu}, uzunluk={uzunluk}, genişlik={genislik}")
    log_oturum_var(f"DOĞRULAMA - Mevcut durum: barkod={barkod}, ağırlık={agirlik}, materyal türü={materyal_turu}, uzunluk={uzunluk}, genişlik={genislik}")

    urun = veritabani_yoneticisi.barkodu_dogrula(barkod)
    
    if not urun:
        sebep = f"Ürün veritabanında yok (Barkod: {barkod})"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_sebep = sebep
        #dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 1, "Ürün veritabanında yok")
        return False

    min_agirlik = urun.get('packMinWeight')
    max_agirlik = urun.get('packMaxWeight')
    min_genislik = urun.get('packMinWidth')
    max_genislik = urun.get('packMaxWidth')
    min_uzunluk = urun.get('packMinHeight')
    max_uzunluk = urun.get('packMaxHeight')
    materyal_id = urun.get('material')   

    print(f"📊 [DOĞRULAMA] Min Agirlik: {min_agirlik}, Max Agirlik: {max_agirlik}, Min Genişlik: {min_genislik}, Max Genişlik: {max_genislik}, Min Uzunluk: {min_uzunluk}, Max Uzunluk: {max_uzunluk}, Materyal_id: {materyal_id}")
    print(f"📊 [DOĞRULAMA] Ölçülen ağırlık: {agirlik} gr")
    log_oturum_var(f"DOĞRULAMA - Min Agirlik: {min_agirlik}, Max Agirlik: {max_agirlik}, Min Genişlik: {min_genislik}, Max Genişlik: {max_genislik}, Min Uzunluk: {min_uzunluk}, Max Uzunluk: {max_uzunluk}, Materyal_id: {materyal_id}")
    log_oturum_var(f"DOĞRULAMA - Ölçülen ağırlık: {agirlik} gr")
    
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
    log_oturum_var(f"DOĞRULAMA - Ağırlık kontrol sonucu: {agirlik_kabul}")

    if not agirlik_kabul:
        sebep = f"Ağırlık sınırları dışında ({agirlik}g)"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_sebep = sebep
        #dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 2, "Ağırlık sınırları dışında")
        return False

    if min_genislik-10 <= genislik <= max_genislik+10:
        print(f"✅ [DOĞRULAMA] Genişlik kontrolü geçti: {genislik} mm")
        log_success(f"DOĞRULAMA - Genişlik kontrolü geçti: {genislik} mm")
    else:
        sebep = f"Genişlik sınırları dışında ({genislik}mm)"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_sebep = sebep
        #dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 3, "Genişlik sınırları dışında")
        return False

    if min_uzunluk-10 <= uzunluk <= max_uzunluk+10 :
        print(f"✅ [DOĞRULAMA] Uzunluk kontrolü geçti: {uzunluk} mm")
        log_success(f"DOĞRULAMA - Uzunluk kontrolü geçti: {uzunluk} mm")
    else:
        sebep = f"Uzunluk sınırları dışında ({uzunluk}mm)"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_sebep = sebep
        #dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 4, "Uzunluk sınırları dışında")
        return False

    if materyal_id != materyal_turu:
        sebep = f"Materyal türü uyuşmuyor (Beklenen: {materyal_id}, Gelen: {materyal_turu})"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_sebep = sebep
        #dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 5, "Materyal türü uyuşmuyor")
        return False
    
    print(f"✅ [DOĞRULAMA] Materyal türü kontrolü geçti: {materyal_turu}")
    log_success(f"DOĞRULAMA - Materyal türü kontrolü geçti: {materyal_turu}")

    kabul_edilen_urun = {
        'barkod': barkod, 'agirlik': agirlik, 'materyal_turu': materyal_turu,
        'uzunluk': uzunluk, 'genislik': genislik,
    }
    sistem.kabul_edilen_urunler.append(kabul_edilen_urun)

    print(f"✅ [DOĞRULAMA] Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    print(f"📦 [KUYRUK] Toplam kabul edilen ürün sayısı: {len(sistem.kabul_edilen_urunler)}")
    log_success(f"DOĞRULAMA - Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    log_oturum_var(f"KUYRUK - Toplam kabul edilen ürün sayısı: {len(sistem.kabul_edilen_urunler)}")

    return True

def uzunluk_dogrulama(uzunluk):
    if sistem.uzunluk_goruntu_isleme-20 <= sistem.uzunluk_motor_verisi <= sistem.uzunluk_goruntu_isleme+20:
        print(f"✅ [UZUNLUK DOĞRULAMA] Uzunluk kontrolü geçti. Motor Uzunluk: {sistem.uzunluk_motor_verisi} mm | Görüntü Uzunluk: {sistem.uzunluk_goruntu_isleme} mm")
        sistem.uzunluk_motor_verisi = None
        sistem.uzunluk_goruntu_isleme = None
        return True
    else:
        print(f"❌ [UZUNLUK DOĞRULAMA] Uzunluk kontrolü başarısız. Motor Uzunluk: {sistem.uzunluk_motor_verisi} mm | Görüntü Uzunluk: {sistem.uzunluk_goruntu_isleme} mm")
        sistem.uzunluk_motor_verisi = None
        sistem.uzunluk_goruntu_isleme = None
        return False

def yeni_urun_ekle(barkod: str = None, agirlik: float = None, materyal: str= None, uzunluk: float = None, genislik: float = None, durum: bool = None, iade_sebep: str = None):
    """
    Yeni bir ürünü gerekli bilgilerle oluşturur ve ana listeye ekler.
    ID ve giriş zamanını otomatik olarak atar.

    Args:
        barkod (str): Ürünün barkodu.
        agirlik (float): Ürünün kilogram cinsinden ağırlığı.
        materyal (str): Ürünün materyal türü (örn: "Plastik", "Metal").
        uzunluk (float): Ürünün santimetre cinsinden uzunluğu.
        genislik (float): Ürünün santimetre cinsinden genişliği.
        durum (str, optional): Ürünün mevcut durumu. Varsayılan: "Giriş Yapıldı".
        iade_sebep (str, optional): Eğer bir iade ise sebebi. Varsayılan: None.
        
    Returns:
        dict: Listeye yeni eklenen ürünün sözlük hali.
    """
    global son_id
    
    # ID'yi bir artır
    son_id += 1
    
    # Yeni ürün için sözlük oluştur
    yeni_urun = {
        "id": son_id,
        "durum": durum,
        "barkod": barkod,
        "agirlik": agirlik,
        "materyal": materyal,
        "uzunluk": uzunluk,
        "genislik": genislik,
        "iade_sebep": iade_sebep,
        "giris_zamani": datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Mevcut zamanı formatla
    }
    
    # Oluşturulan yeni ürünü ana listeye ekle
    urun_listesi.append(yeni_urun)
    
    print(f"✅ ID: {son_id} olan '{barkod}' barkodlu ürün listeye başarıyla eklendi.")
    
    return yeni_urun

def yonlendirici():

    if not sistem.kabul_edilen_urunler:
        print(f"⚠️ [YÖNLENDİRME] Kabul edilen ürün kuyruğu boş.")
        sistem.iade_sebep = "Yönlendirme için ürün yok."
        sistem.kabul_edilen_urunler.clear()  # Tüm kabul edilen ürünleri temizle
        return False
        
    sistem.uzunluk_motor_verisi = sistem.motor_ref.atik_uzunluk()
    time.sleep(0.05)  # Ölçüm için bekleme süresi 
    print(f"📏 [YÖNLENDİRME] Motor uzunluk verisi: {sistem.uzunluk_motor_verisi} mm")
    if sistem.uzunluk_motor_verisi:
        if uzunluk_dogrulama(sistem.uzunluk_motor_verisi):
            print(f"✅ [YÖNLENDİRME] Uzunluk Verisi Doğrulandı.")
        else:
            print(f"❌ [YÖNLENDİRME] Uzunluk Verisi Uyuşmazlığı.")
            sistem.iade_sebep = "Uzunluk Verisi Uyuşmazlığı"
            sistem.kabul_edilen_urunler.clear()  # Tüm kabul edilen ürünleri temizle
            return False
    else:
        print(f"⚠️ [YÖNLENDİRME] Uzunluk Verisi Gelmedi")
        sistem.iade_sebep = "Uzunluk Verisi Uyuşmazlığı"
        sistem.kabul_edilen_urunler.clear()  # Tüm kabul edilen ürünleri temizle
        return False

    urun = sistem.kabul_edilen_urunler[0]
    print(f"📦 [YÖNLENDİRME] İşlenecek ürün: {urun}")
    materyal_id = urun.get('materyal_turu')
    
    materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
    materyal_adi = materyal_isimleri.get(materyal_id, "BİLİNMEYEN")
    
    print(f"\n🔄 [YÖNLENDİRME] {materyal_adi} ürün işleniyor: {urun['barkod']}")

    if sistem.motor_ref:
        if materyal_id == 2: # Cam
            if sistem.kirici_durum:
                manuel_kirici_kontrol("ileri_10sn")
            sistem.motor_ref.yonlendirici_cam()
            print(f"🟦 [CAM] Cam yönlendiricisine gönderildi")
        elif materyal_id == 1 or materyal_id == 3: # Plastik/Metal
            if sistem.ezici_durum:
                manuel_ezici_kontrol("ileri_10sn")  # Otomatik ezici 10 saniye ileri
            sistem.motor_ref.yonlendirici_plastik()
            print(f"🟩 [PLASTİK/METAL] Plastik/Metal yönlendiricisine gönderildi")
        else:
            print(f"❌ [YÖNLENDİRME] Bilinmeyen materyal türü: {materyal_id}. İade ediliyor.")
            sistem.iade_sebep = "Bilinmeyen materyal türü"
            return False
    else:
        print("❌ [YÖNLENDİRME] Motor referansı ayarlı değil!")
        log_error("YÖNLENDİRME - Motor referansı ayarlı değil!")
        return False

    return True
    sistem.kabul_edilen_urunler.popleft()
    print(f"📦 [KUYRUK] Kalan ürün sayısı: {len(sistem.kabul_edilen_urunler)}")

def lojik_yoneticisi():
    while True:
        time.sleep(0.005)

        # Durum 1: BEKLEMEDE
        # Sistem boştur ve ürünün yerleştirilmesini (GSI sinyali) bekler.
        if sistem.akis_durumu == SistemAkisDurumu.BEKLEMEDE:
            if sistem.gsi_lojik:
                sistem.gsi_lojik = False # Gelen sinyali işledik, sıfırla.
                sistem.motor_ref.konveyor_ileri()
                sistem.akis_durumu = SistemAkisDurumu.GIRIS_ALGILANDI

            if sistem.ysi_lojik or sistem.yso_lojik:
                sistem.ysi_lojik = False
                sistem.yso_lojik = False
                print("⚠️ [YÖNLENDİRİCİ] Beklenmeyen YSI/YSO sinyali! İade ediliyor.")
                sistem.iade_sebep = "Beklenmeyen YSI/YSO sinyali"
                sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                sistem.motor_ref.konveyor_geri()

            else:
                lojik_sifirlama()
        # Durum 2: GIRIS_ALGILANDI
        # Konveyör ilerliyor ve ürünün tamamen girmesini (GSO sinyali) bekler.
        elif sistem.akis_durumu == SistemAkisDurumu.GIRIS_ALGILANDI:
            if sistem.gso_lojik:
                sistem.gso_lojik = False # Gelen sinyali işledik, sıfırla.
                
                # Kritik Kontrol: Bu noktada barkod verisi gelmiş mi?
                if sistem.mevcut_barkod is None:
                    
                    print("❌ [GSO] Ürün içeride ama barkod yok! İade ediliyor...")
                    sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                    sistem.motor_ref.konveyor_geri()

                else:
                    # Barkod gelmişse, doğrulama adımları başlar.
                    print(f"✅ [GSO] Ürün içeride. Barkod: {sistem.mevcut_barkod}. Doğrulama başlıyor.")
                    sistem.akis_durumu = SistemAkisDurumu.VERI_BEKLENIYOR
                    sistem.barkod_lojik = False # Barkod işlendi, sıfırla.
                    sistem.sensor_ref.loadcell_olc()
                    goruntu_isleme_tetikle()
        
            else:
                lojik_sifirlama()

        # Görevi: Tüm verilerin gelip gelmediğini sürekli kontrol etmek.
        elif sistem.akis_durumu == SistemAkisDurumu.VERI_BEKLENIYOR:
            # Gerekli tüm verilerin gelip gelmediğini kontrol et
            veriler_tamam_mi = all([
                sistem.mevcut_barkod is not None,
                sistem.mevcut_agirlik is not None,
                sistem.mevcut_materyal_turu is not None,
                sistem.mevcut_uzunluk is not None,
                sistem.mevcut_genislik is not None
            ])

            if veriler_tamam_mi:
                print("✅ Tüm veriler toplandı. Nihai doğrulama yapılıyor.")
                # Orijinal doğrulama fonksiyonunuzu burada çağırın

                sonuc_basarili_mi = dogrulama(sistem.mevcut_barkod, sistem.mevcut_agirlik, sistem.mevcut_materyal_turu, sistem.mevcut_uzunluk, sistem.mevcut_genislik) 

                if sonuc_basarili_mi:
                    print("👍 Doğrulama başarılı. Yönlendirme durumuna geçiliyor.")
                    sistem.akis_durumu = SistemAkisDurumu.YONLENDIRICI_KABUL

                else:
                    print("👎 Doğrulama başarısız. İade ediliyor.")
                    # dogrulama fonksiyonu iade sebebini 'sistem.iade_sebep'e yazmalı
                    sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                
                # Bir sonraki ürün için geçici verileri temizle
                sistem.mevcut_barkod = None
                sistem.mevcut_agirlik = None
                sistem.mevcut_materyal_turu = None
                sistem.mevcut_uzunluk = None
                sistem.mevcut_genislik = None
            
            if sistem.gso_lojik:
                sistem.gso_lojik = False # Gelen sinyali işledik, sıfırla.
                
                # Kritik Kontrol: Bu noktada barkod verisi gelmiş mi?
                if sistem.mevcut_barkod is None:
                    
                    print("❌ [GSO] Ürün içeride ama barkod yok! İade ediliyor...")
                    sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                    sistem.motor_ref.konveyor_geri()

                else:
                    # Barkod gelmişse, doğrulama adımları başlar.
                    print(f"✅ [GSO] Ürün içeride. Barkod: {sistem.mevcut_barkod}. Doğrulama başlıyor.")
                    sistem.akis_durumu = SistemAkisDurumu.VERI_BEKLENIYOR
                    sistem.sensor_ref.loadcell_olc()
                    goruntu_isleme_tetikle()

            
            lojik_sifirlama()
        
        # Durum 5: YONLENDİRİCİ KABUL
        elif sistem.akis_durumu == SistemAkisDurumu.YONLENDIRICI_KABUL:
            if sistem.yso_lojik:
                sistem.yso_lojik = False
                print("✅ [YSO] Ürün yönlendiriciye ulaştı.")
                sistem.motor_ref.konveyor_dur()
                yonlendirici_basarili = yonlendirici()
                if yonlendirici_basarili:
                    print("👍 Yönlendirme başarılı. Ürün yönlendiriciye gönderildi.")
                    sistem.akis_durumu = SistemAkisDurumu.YONLENDIRICI_HAREKET
                    # Bir sonraki ürün için geçici verileri temizle
                    sistem.mevcut_barkod = None
                    sistem.mevcut_agirlik = None
                    sistem.mevcut_materyal_turu = None
                    sistem.mevcut_uzunluk = None
                    sistem.mevcut_genislik = None
                else:
                    print("❌ Yönlendirme başarısız. İade ediliyor.")
                    sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                    sistem.motor_ref.konveyor_geri()
            # Bu kısım ürünün yönlendiriciye ulaştığını (YSO) bekler
            else:
                lojik_sifirlama()

        elif sistem.akis_durumu == SistemAkisDurumu.YONLENDIRICI_HAREKET:
            if sistem.yonlendirici_konumda:
                sistem.yonlendirici_konumda = False
                print("✅ [YONLENDİRİCİ] Ürün yönlendirildi. Sistem bekleme moduna dönüyor.")
                sistem.akis_durumu = SistemAkisDurumu.BEKLEMEDE

            elif sistem.yonlendirici_hata:
                sistem.yonlendirici_hata = False
                print("❌ [YONLENDİRİCİ] Hata oluştu! Ürün iade ediliyor.")
                sistem.iade_sebep = "Yönlendirici hatası"
                sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                sistem.motor_ref.konveyor_geri()
            
            elif sistem.yonlendirici_alarm:
                sistem.yonlendirici_alarm = False
                print("⚠️ [YONLENDİRİCİ] Alarm durumu! Ürün iade ediliyor.")
                sistem.iade_sebep = "Yönlendirici alarmı"
                sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                sistem.motor_ref.konveyor_geri()

            elif sistem.ysi_lojik or sistem.yso_lojik:
                sistem.ysi_lojik = False
                sistem.yso_lojik = False
                print("⚠️ [YONLENDİRİCİ] Beklenmeyen YSI/YSO sinyali! İade ediliyor.")
                sistem.motor_ref.yonlendirici_dur()
                sistem.iade_sebep = "Beklenmeyen YSI/YSO sinyali"
                sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                sistem.motor_ref.konveyor_geri()
            else:
                lojik_sifirlama()

        elif sistem.akis_durumu == SistemAkisDurumu.IADE_EDILIYOR:
            # İstenen davranış: İade modundayken gelen GSI sinyallerini yok say.
            if sistem.gsi_lojik:
                sistem.gsi_lojik = False # Sinyali tüket ama hiçbir şey yapma.
                time.sleep(0.25)
                sistem.motor_ref.konveyor_dur()
                print("⚠️ [GSI] İade modunda ürünü lütfen alınız.")
            
            # İade edilen ürün alındığında tekrar GSO sinyali gelir.
            
            elif sistem.ysi_lojik or sistem.yso_lojik:
                sistem.ysi_lojik = False
                sistem.yso_lojik = False
                print("⚠️ [YÖNLENDİRİCİ] Beklenmeyen YSI/YSO sinyali! İade işlemine devam ediliyor.")
                sistem.motor_ref.konveyor_geri()
            
            elif sistem.gso_lojik:
                sistem.gso_lojik = False
                goruntu = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
                print(f"📷 [GÖRÜNTÜ İŞLEME - İADE] Sonuç: {goruntu}")
                if goruntu.mesaj=="nesne_yok":
                    print("👍 Ürün geri alındı. Sistem normale dönüyor.")
                    time.sleep(2)
                    sistem.akis_durumu = SistemAkisDurumu.BEKLEMEDE
                    sistem.mevcut_barkod = None
                    sistem.mevcut_agirlik = None
                    sistem.mevcut_materyal_turu = None
                    sistem.mevcut_uzunluk = None
                    sistem.mevcut_genislik = None
                    lojik_sifirlama()
                else:
                    print("❌ Ürün geri alınamadı veya konveyörde başka ürün var. İade işlemine devam ediliyor.")
                    sistem.motor_ref.konveyor_geri()

            else:
                lojik_sifirlama()

def lojik_sifirlama():



    sistem.gsi_lojik = False
    sistem.gso_lojik = False
    sistem.ysi_lojik = False
    sistem.yso_lojik = False
    sistem.ezici_durum = False
    sistem.kirici_durum = False

    # Alarmlar
    sistem.konveyor_alarm = False
    sistem.yonlendirici_alarm = False
    sistem.seperator_alarm = False
    
    # Konumlar
    sistem.konveyor_konumda = False
    sistem.yonlendirici_konumda = False
    sistem.seperator_konumda = False
    
    # Hatalar
    sistem.konveyor_hata = False
    sistem.yonlendirici_hata = False
    sistem.seperator_hata = False
    sistem.konveyor_adim_problem = False
    
    # Kalibrasyonlar
    sistem.yonlendirici_kalibrasyon = False
    sistem.seperator_kalibrasyon = False

def mesaj_isle(mesaj):
    mesaj = mesaj.strip().lower()
    
    if mesaj == "oturum_var":
        if not sistem.lojik_thread_basladi:
            print("🟢 [OTURUM] Aktif oturum başlatıldı")
            log_oturum_var("OTURUM - Aktif oturum başlatıldı")
            t1 = threading.Thread(target=lojik_yoneticisi, daemon=True)
            t1.start()
            sistem.lojik_thread_basladi = True
        else:
            print("⚠️ [OTURUM] Lojik yöneticisi zaten çalışıyor, yeni thread başlatılmadı.")
            log_warning("OTURUM - Lojik yöneticisi zaten çalışıyor, yeni thread başlatılmadı.")

        sistem.akis_durumu = SistemAkisDurumu.BEKLEMEDE
        sistem.kabul_edilen_urunler.clear()
        sistem.uzunluk_goruntu_isleme = None
        sistem.uzunluk_motor_verisi = None

        sistem.motor_ref.motorlari_aktif_et()
        sistem.motor_ref.konveyor_geri()
        sistem.sensor_ref.tare()
        sistem.sensor_ref.led_ac()
        time.sleep(2)
        sistem.motor_ref.konveyor_dur()
        sistem.sensor_ref.makine_oturum_var()
        sistem.ezici_durum = False
        sistem.kirici_durum = False

    if mesaj.startswith("a:"):
    # Sadece veri bekliyorsak ağırlığı kaydet
        if sistem.akis_durumu == SistemAkisDurumu.VERI_BEKLENIYOR:
            agirlik = float(mesaj.split(":")[1].replace(",", "."))
            sistem.mevcut_agirlik = agirlik
            agirlik = None
            print(f"⚖️ Ağırlık verisi alındı: {agirlik} gr")
        else:
            print(f"⚠️ Ağırlık verisi geldi ama sistem beklemiyordu. Yok sayıldı.")

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
    if mesaj == "kmp":  
        sistem.konveyor_adim_problem = True
    if mesaj == "ykt":
        sistem.yonlendirici_kalibrasyon = True
    if mesaj == "skt":  
        sistem.seperator_kalibrasyon = True
    
def modbus_mesaj(modbus_verisi):
    veri = modbus_verisi
    #print(f"[Oturum Var Modbus] Gelen veri: {modbus_verisi}")

sistem = SistemDurumu()
goruntu_isleme_servisi = GoruntuIslemeServisi()
veri_lock = threading.Lock()