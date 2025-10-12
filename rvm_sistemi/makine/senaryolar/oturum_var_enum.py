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

class SistemAkisDurumu(Enum):
    BEKLEMEDE = auto()          # Sistem yeni bir ürünün yerleştirilmesini (GSI) bekliyor.
    GIRIS_ALGILANDI = auto()    # Ürün algılandı (GSI), konveyörde ilerliyor, GSO bekleniyor.
    DOGRULAMA_BASLADI = auto()  # GSO ve barkod OK. Asenkron veri toplama işlemlerini TETİKLE.
    VERI_BEKLENIYOR = auto()    # Ağırlık ve görüntü verilerinin gelmesini BEKLE.
    YONLENDIRME = auto()        # Doğrulama başarılı, ürün yönlendiriciye gidiyor.
    IADE_EDILIYOR = auto()      # Hata/Başarısız doğrulama, ürün iade ediliyor.

@dataclass
class Urun:
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    barkod: str = None
    agirlik: float = None
    uzunluk: float = None
    genislik: float = None
    materyal_turu: int = None
    akis_durumu: SistemAkisDurumu = SistemAkisDurumu.BEKLEMEDE
    durum_zamani: float = field(default_factory=time.time)
    iade_sebep: str = None

@dataclass
class SistemDurumu:

    akis_durumu: SistemAkisDurumu = SistemAkisDurumu.BEKLEMEDE
    mevcut_barkod: str = None
    
    # Doğrulama için gelen verileri tutacak alanlar
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
    veri_senkronizasyon_listesi: list = field(default_factory=list)
    kabul_edilen_urunler: deque = field(default_factory=deque)
    onaylanan_urunler: list = field(default_factory=list)
    agirlik_kuyruk: deque = field(default_factory=deque)  # Ağırlık kuyruğu
    
    # İade Sebep String
    iade_sebep: str = None

    # Lojikler
    iade_etildi: bool = False
    lojik_thread_basladi: bool = False
    konveyor_durum_kontrol: bool = False
    yonlendirici_iade: bool = False
    yonlendirici_calisiyor: bool = False
    iade_lojik: bool = False
    kabul_yonu: bool = True
    iade_lojik_onceki_durum: bool = False
    barkod_lojik: bool = False
    gsi_lojik: bool = False
    gsi_gecis_lojik: bool = False
    giris_sensor_durum: bool = False
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
    
    # Son işlenen ürün bilgisi (ymk için)
    son_islenen_urun: dict = None
    
# 🌍 Tekil (global) sistem nesneleri
sistem = SistemDurumu()
goruntu_isleme_servisi = GoruntuIslemeServisi()
veri_lock = threading.Lock() # Eş zamanlı erişimi kontrol etmek için Kilit mekanizması

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
    if sistem.akis_durumu in [SistemAkisDurumu.BEKLEMEDE, SistemAkisDurumu.GIRIS_ALGILANDI]:
         sistem.mevcut_barkod = barcode
         print(f"🔗 [{barcode}] Barkod alındı.")
    else:
         print(f"⚠️ Barkod okundu ama sistem ürün kabul etmiyor. Durum: {sistem.akis_durumu}")

def goruntu_isleme_tetikle():
    """Görüntü işlemeyi tetikler ve sonuçları veri senkronizasyonuna gönderir"""
    goruntu_sonuc = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
    print(f"\n📷 [GÖRÜNTÜ İŞLEME] Sonuç: {goruntu_sonuc}")
    log_oturum_var(f"GÖRÜNTÜ İŞLEME - Sonuç: {goruntu_sonuc}")
    sistem.uzunluk_goruntu_isleme = float(goruntu_sonuc.genislik_mm)
    veri_senkronizasyonu(
        materyal_turu=goruntu_sonuc.tur.value, 
        uzunluk=float(goruntu_sonuc.genislik_mm), 
        genislik=float(goruntu_sonuc.yukseklik_mm)
    )

def veri_senkronizasyonu(materyal_turu=None, uzunluk=None, genislik=None):
    # Sadece veri bekliyorsak verileri kaydet
    if sistem.akis_durumu == SistemAkisDurumu.VERI_BEKLENIYOR:
        sistem.mevcut_materyal_turu = materyal_turu
        sistem.mevcut_uzunluk = uzunluk
        sistem.mevcut_genislik = genislik
        print(f"📷 Görüntü işleme verileri alındı.")
    else:
        print(f"⚠️ Görüntü işleme verisi geldi ama sistem beklemiyordu. Yok sayıldı.")

def dogrulama(barkod, agirlik, materyal_turu, uzunluk, genislik):

    print(f"\n📊 [DOĞRULAMA] Mevcut durum: barkod={barkod}, ağırlık={agirlik}, materyal türü={materyal_turu}, uzunluk={uzunluk}, genişlik={genislik}")
    log_oturum_var(f"DOĞRULAMA - Mevcut durum: barkod={barkod}, ağırlık={agirlik}, materyal türü={materyal_turu}, uzunluk={uzunluk}, genişlik={genislik}")

    urun = veritabani_yoneticisi.barkodu_dogrula(barkod)
    
    if not urun:
        sebep = f"Ürün veritabanında yok (Barkod: {barkod})"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 1, "Ürün veritabanında yok")
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
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 2, "Ağırlık sınırları dışında")
        return

    if min_genislik-10 <= genislik <= max_genislik+10:
        print(f"✅ [DOĞRULAMA] Genişlik kontrolü geçti: {genislik} mm")
        log_success(f"DOĞRULAMA - Genişlik kontrolü geçti: {genislik} mm")
    else:
        sebep = f"Genişlik sınırları dışında ({genislik}mm)"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 3, "Genişlik sınırları dışında")
        return

    if min_uzunluk-10 <= uzunluk <= max_uzunluk+10 :
        print(f"✅ [DOĞRULAMA] Uzunluk kontrolü geçti: {uzunluk} mm")
        log_success(f"DOĞRULAMA - Uzunluk kontrolü geçti: {uzunluk} mm")
    else:
        sebep = f"Uzunluk sınırları dışında ({uzunluk}mm)"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 4, "Uzunluk sınırları dışında")
        return

    if materyal_id != materyal_turu:
        sebep = f"Materyal türü uyuşmuyor (Beklenen: {materyal_id}, Gelen: {materyal_turu})"
        print(f"❌ [DOĞRULAMA] {sebep}")
        log_error(f"DOĞRULAMA - {sebep}")
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik, False, 5, "Materyal türü uyuşmuyor")
        return
    
    print(f"✅ [DOĞRULAMA] Materyal türü kontrolü geçti: {materyal_turu}")
    log_success(f"DOĞRULAMA - Materyal türü kontrolü geçti: {materyal_turu}")

    kabul_edilen_urun = {
        'barkod': barkod, 'agirlik': agirlik, 'materyal_turu': materyal_turu,
        'uzunluk': uzunluk, 'genislik': genislik,
    }
    sistem.kabul_edilen_urunler.append(kabul_edilen_urun)
    sistem.onaylanan_urunler.append(kabul_edilen_urun.copy())

    print(f"✅ [DOĞRULAMA] Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    print(f"📦 [KUYRUK] Toplam kabul edilen ürün sayısı: {len(sistem.kabul_edilen_urunler)}")
    log_success(f"DOĞRULAMA - Ürün kabul edildi ve kuyruğa eklendi: {barkod}")
    log_oturum_var(f"KUYRUK - Toplam kabul edilen ürün sayısı: {len(sistem.kabul_edilen_urunler)}")
    


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

def yonlendirici_hareket():

    if not sistem.kabul_edilen_urunler:
        print(f"⚠️ [YÖNLENDİRME] Kabul edilen ürün kuyruğu boş.")
        sistem.iade_lojik = True
        sistem.iade_sebep = "Yönlendirme için ürün yok."
        sistem.veri_senkronizasyon_listesi.clear()  # Tüm bekleyen verileri temizle
        sistem.kabul_edilen_urunler.clear()  # Tüm kabul edilen ürünleri temizle
        sistem.agirlik_kuyruk.clear()  # Tüm bekleyen ağırlıkları temizle
        return
    sistem.uzunluk_motor_verisi = sistem.motor_ref.atik_uzunluk()
    time.sleep(0.05)  # Ölçüm için bekleme süresi 
    print(f"📏 [YÖNLENDİRME] Motor uzunluk verisi: {sistem.uzunluk_motor_verisi} mm")
    if sistem.uzunluk_motor_verisi:
        if uzunluk_dogrulama(sistem.uzunluk_motor_verisi):
            print(f"✅ [YÖNLENDİRME] Uzunluk Verisi Doğrulandı.")
        else:
            print(f"❌ [YÖNLENDİRME] Uzunluk Verisi Uyuşmazlığı.")
            sistem.iade_lojik = True
            sistem.iade_sebep = "Uzunluk Verisi Uyuşmazlığı"
            sistem.veri_senkronizasyon_listesi.clear()  # Tüm bekleyen verileri temizle
            sistem.kabul_edilen_urunler.clear()  # Tüm kabul edilen ürünleri temizle
            sistem.agirlik_kuyruk.clear()  # Tüm bekleyen ağırlıkları temizle
            return
    else:
        print(f"⚠️ [YÖNLENDİRME] Uzunluk Verisi Gelmedi")
        sistem.iade_lojik = True
        sistem.iade_sebep = "Uzunluk Verisi Uyuşmazlığı"
        sistem.veri_senkronizasyon_listesi.clear()  # Tüm bekleyen verileri temizle
        sistem.kabul_edilen_urunler.clear()  # Tüm kabul edilen ürünleri temizle
        sistem.agirlik_kuyruk.clear()  # Tüm bekleyen ağırlıkları temizle
        return

    urun = sistem.kabul_edilen_urunler[0]
    print(f"📦 [YÖNLENDİRME] İşlenecek ürün: {urun}")
    sistem.son_islenen_urun = urun.copy()
    materyal_id = urun.get('materyal_turu')
    
    materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
    materyal_adi = materyal_isimleri.get(materyal_id, "BİLİNMEYEN")
    
    print(f"\n🔄 [YÖNLENDİRME] {materyal_adi} ürün işleniyor: {urun['barkod']}")

    sistem.yonlendirici_calisiyor = True
    if sistem.motor_ref:
        if materyal_id == 2: # Cam
            if sistem.kirici_durum:
                manuel_kirici_kontrol("ileri_10sn")
            sistem.motor_ref.konveyor_dur()
            sistem.motor_ref.yonlendirici_cam()
            print(f"🟦 [CAM] Cam yönlendiricisine gönderildi")
        else: # Plastik/Metal
            if sistem.ezici_durum:
                manuel_ezici_kontrol("ileri_10sn")  # Otomatik ezici 10 saniye ileri
            sistem.motor_ref.konveyor_dur()
            sistem.motor_ref.yonlendirici_plastik()
            print(f"🟩 [PLASTİK/METAL] Plastik/Metal yönlendiricisine gönderildi")
    
    sistem.kabul_edilen_urunler.popleft()
    print(f"📦 [KUYRUK] Kalan ürün sayısı: {len(sistem.kabul_edilen_urunler)}")
    print(f"✅ [YÖNLENDİRME] İşlem tamamlandı\n")

def lojik_yoneticisi():
    while True:
        time.sleep(0.005)

        # Durum 1: BEKLEMEDE
        # Sistem boştur ve ürünün yerleştirilmesini (GSI sinyali) bekler.
        if sistem.akis_durumu == SistemAkisDurumu.BEKLEMEDE:
            if sistem.gsi_lojik:
                sistem.gsi_lojik = False # Gelen sinyali işledik, sıfırla.
                print("➡️ [GSI] Giriş algılandı. Konveyör ileri...")
                sistem.motor_ref.konveyor_ileri()
                sistem.akis_durumu = SistemAkisDurumu.GIRIS_ALGILANDI

        # Durum 2: GIRIS_ALGILANDI
        # Konveyör ilerliyor ve ürünün tamamen girmesini (GSO sinyali) bekler.
        elif sistem.akis_durumu == SistemAkisDurumu.GIRIS_ALGILANDI:
            if sistem.gso_lojik:
                sistem.gso_lojik = False # Gelen sinyali işledik, sıfırla.
                
                # Kritik Kontrol: Bu noktada barkod verisi gelmiş mi?
                if sistem.mevcut_barkod is None:
                    print("❌ [GSO] Ürün içeride ama barkod yok! İade ediliyor...")
                    sistem.akis_durumu = SistemAkisDurumu.IADE_EDILIYOR
                    # Konveyörü 1 saniye geri çevirme işlemi burada tetiklenmeli.
                    sistem.motor_ref.konveyor_geri()
                    time.sleep(1)
                    sistem.motor_ref.konveyor_dur()
                else:
                    # Barkod gelmişse, doğrulama adımları başlar.
                    print(f"✅ [GSO] Ürün içeride. Barkod: {sistem.mevcut_barkod}. Doğrulama başlıyor.")
                    sistem.akis_durumu = SistemAkisDurumu.DOGRULAMA_BASLADI
        

        # Durum 3: DOGRULAMA_BASLADI
        # Görevi: Asenkron işlemleri BİR KEZ tetiklemek ve durumu değiştirmek.
        elif sistem.akis_durumu == SistemAkisDurumu.DOGRULAMA_BASLADI:
            print("⚖️ Görüntü işleme ve ağırlık ölçümü tetikleniyor...")
            sistem.akis_durumu = SistemAkisDurumu.VERI_BEKLENIYOR
            sistem.sensor_ref.loadcell_olc()
            goruntu_isleme_tetikle()
            

        # Durum 4: VERI_BEKLENIYOR
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
                # sonuc_basarili_mi = dogrulama(sistem.mevcut_barkod, sistem.mevcut_agirlik, ...)
                dogrulama(sistem.mevcut_barkod, sistem.mevcut_agirlik, sistem.mevcut_materyal_turu, sistem.mevcut_uzunluk, sistem.mevcut_genislik) 
                sonuc_basarili_mi = True # Örnek olarak True varsayalım

                if sonuc_basarili_mi:
                    print("👍 Doğrulama başarılı. Yönlendirme durumuna geçiliyor.")
                    sistem.akis_durumu = SistemAkisDurumu.YONLENDIRME
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
        
        # Durum 5: YONLENDIRME
        elif sistem.akis_durumu == SistemAkisDurumu.YONLENDIRME:
            if sistem.yso_lojik:
                sistem.yso_lojik = False
                print("✅ [YSO] Ürün yönlendiriciye ulaştı.")
                yonlendirici_hareket()
                sistem.akis_durumu = SistemAkisDurumu.BEKLEMEDE
                # Bir sonraki ürün için geçici verileri temizle
                sistem.mevcut_barkod = None
                sistem.mevcut_agirlik = None
                sistem.mevcut_materyal_turu = None
                sistem.mevcut_uzunluk = None
                sistem.mevcut_genislik = None
            # Bu kısım ürünün yönlendiriciye ulaştığını (YSO) bekler
            print("🚚 Ürün yönlendiriciye doğru ilerliyor...")
            # yso_lojik gelince işlem tamamlanır ve BEKLEMEDE'ye dönülür.
            pass


        elif sistem.akis_durumu == SistemAkisDurumu.IADE_EDILIYOR:
            # İstenen davranış: İade modundayken gelen GSI sinyallerini yok say.
            if sistem.gsi_lojik:
                sistem.gsi_lojik = False # Sinyali tüket ama hiçbir şey yapma.
                print("⚠️ [IADE MODU] GSI sinyali yok sayıldı.")
            
            # İade edilen ürün alındığında tekrar GSO sinyali gelir.
            if sistem.gso_lojik:
                sistem.gso_lojik = False
                print("👍 Ürün geri alındı. Sistem normale dönüyor.")
                # Konveyörün durduğundan emin ol
                # sistem.motor_ref.konveyor_dur()
                sistem.akis_durumu = SistemAkisDurumu.BEKLEMEDE
                sistem.mevcut_barkod = None # Barkod bilgisini temizle


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
        sistem.iade_lojik = False
        sistem.iade_lojik_onceki_durum = False
        sistem.barkod_lojik = False
        sistem.veri_senkronizasyon_listesi.clear()
        sistem.kabul_edilen_urunler.clear()
        sistem.onaylanan_urunler.clear()
        sistem.uzunluk_goruntu_isleme = None
        sistem.agirlik_kuyruk.clear()
        sistem.uzunluk_motor_verisi = None

        sistem.motor_ref.motorlari_aktif_et()
        sistem.sensor_ref.tare()
        sistem.motor_ref.konveyor_dur()
        sistem.sensor_ref.led_ac()
        sistem.kabul_yonu = True
        sistem.ezici_durum = False
        sistem.kirici_durum = False

    if mesaj.startswith("a:"):
    # Sadece veri bekliyorsak ağırlığı kaydet
        if sistem.akis_durumu == SistemAkisDurumu.VERI_BEKLENIYOR:
            agirlik = float(mesaj.split(":")[1].replace(",", "."))
            sistem.mevcut_agirlik = agirlik
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