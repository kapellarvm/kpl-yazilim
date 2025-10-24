import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
import threading
from ..goruntu.goruntu_isleme_servisi import GoruntuIslemeServisi
import uuid as uuid_lib
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from . import uyari
from ...utils.logger import log_oturum_var, log_error, log_success, log_warning, log_system
from ...dimdb.hata_kodlari import AcceptPackageResultCodes, hata_kodu_al, hata_mesaji_al

# ==================== SABITLER ====================
AGIRLIK_TOLERANSI = 200  # gram
UZUNLUK_TOLERANSI = 100  # mm
GENISLIK_TOLERANSI = 100  # mm
UZUNLUK_DOGRULAMA_TOLERANSI = 200  # mm
LOJIK_DONGU_BEKLEME = 0.005  # saniye
UZUNLUK_OLCUM_BEKLEME = 0.05  # saniye
OTURUM_BASLANGIC_BEKLEME = 2  # saniye
print("XXXXXXXXXXXXXXXXXX-----MEVLANA MOD AÇIK !!!!------XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

MATERYAL_ISIMLERI = {
    1: "PET",
    2: "CAM", 
    3: "ALÜMİNYUM"
}

@dataclass
class SistemDurumu:
    # Referanslar
    motor_ref: Optional[object] = None
    sensor_ref: Optional[object] = None
    motor_kontrol_ref: Optional[object] = None
    
    # Veriler
    agirlik: Optional[float] = None
    uzunluk_motor_verisi: Optional[float] = None
    iade_sebep: Optional[str] = None
    
    # Listeler
    veri_senkronizasyon_listesi: List[Dict] = field(default_factory=list)
    kabul_edilen_urunler: deque = field(default_factory=deque)
    onaylanan_urunler: List[Dict] = field(default_factory=list)
    agirlik_kuyruk: deque = field(default_factory=deque)
    uzunluk_goruntu_kuyruk: deque = field(default_factory=deque)  # Görüntü uzunluk kuyruğu
    
    # Durum Bayrakları
    iade_etildi: bool = False
    lojik_thread_basladi: bool = False
    konveyor_durum_kontrol: bool = False
    

    yonlendirici_iade: bool = False
    yonlendirici_calisiyor: bool = False
    iade_lojik: bool = False
    kabul_yonu: bool = True
    iade_lojik_onceki_durum: bool = False
    barkod_lojik: bool = False
    
    # Sensör Lojiği
    gsi_lojik: bool = False
    gsi_gecis_lojik: bool = False
    giris_sensor_durum: bool = False
    gso_lojik: bool = False
    ysi_lojik: bool = False
    yso_lojik: bool = False
    
    # Motor Durumları
    ezici_durum: bool = False
    kirici_durum: bool = False
    
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
    konveyor_adim_problem: bool = False
    
    # Kalibrasyonlar
    yonlendirici_kalibrasyon: bool = False
    seperator_kalibrasyon: bool = False
    
    # Oturum Bilgisi
    aktif_oturum: Dict = field(default_factory=lambda: {
        "aktif": False,
        "sessionId": None,
        "userId": None,
        "paket_uuid_map": {}
    })
    
    # Uyku modu durumu
    uyku_modu_aktif: bool = False
    
    # UPS Durumu
    ups_kesintisi: bool = False
    ups_kesinti_zamani: Optional[float] = None
    gsi_bekleme_durumu: bool = False
    
    son_islenen_urun: Optional[Dict] = None
    sistem_calisma_durumu: bool = True

# ==================== GLOBAL OBJELER ====================
sistem = SistemDurumu()
goruntu_isleme_servisi = GoruntuIslemeServisi()
veri_lock = threading.Lock()

# ==================== YARDIMCI FONKSİYONLAR ====================

def sistem_temizle():
    """Sistem state'ini temizler"""
    sistem.veri_senkronizasyon_listesi.clear()
    sistem.kabul_edilen_urunler.clear()
    sistem.agirlik_kuyruk.clear()
    sistem.uzunluk_goruntu_kuyruk.clear()
    sistem.barkod_lojik = False
    # Sistem temizlendi - sadece log dosyasına yazılır
    log_system("Sistem durumu temizlendi")

def dimdb_bildirim_gonder(barcode: str, agirlik: float, materyal_turu: int, 
                          uzunluk: float, genislik: float, kabul_edildi: bool, 
                          sebep_kodu: int, sebep_mesaji: str):
    """DİM-DB'ye bildirim gönderir"""
    try:
        from ...dimdb.dimdb_yoneticisi import dimdb_bildirim_gonder as sunucu_dimdb_bildirim
        sunucu_dimdb_bildirim(barcode, agirlik, materyal_turu, uzunluk, 
                             genislik, kabul_edildi, sebep_kodu, sebep_mesaji)
    except Exception as e:
        log_error(f"DİM-DB bildirim hatası: {e}")

# ==================== REFERANS YÖNETİMİ ====================

def motor_referansini_ayarla(motor):
    sistem.motor_ref = motor
    sistem.motor_ref.yonlendirici_sensor_teach()
    # Motor hazır - sadece log dosyasına yazılır
    log_oturum_var("Motor hazır - Sistem başlatıldı")

def sensor_referansini_ayarla(sensor):
    sistem.sensor_ref = sensor
    sistem.sensor_ref.teach()
    # Sensör hazır - sadece log dosyasına yazılır

def motor_kontrol_referansini_ayarla(motor_kontrol):
    sistem.motor_kontrol_ref = motor_kontrol
    # Motor kontrol referansı ayarlandı - sadece log dosyasına yazılır
    log_oturum_var("Motor kontrol referansı ayarlandı")

# ==================== BARKOD İŞLEME ====================

def barkod_verisi_al(barcode: str):
    """Barkod okuma ve UUID ataması"""
    if sistem.iade_lojik:
        print(f"🚫 [BARKOD] İade aktif - Barkod görmezden gelindi: {barcode}")
        log_warning(f"İade aktif - Barkod görmezden gelindi: {barcode}")
        return
    
    if sistem.barkod_lojik:
        print(f"⚠️ [BARKOD] Kuyruk dolu - Barkod görmezden gelindi: {barcode}")
        log_warning(f"Kuyruk dolu - Barkod görmezden gelindi: {barcode}")
        return
    
    paket_uuid = str(uuid_lib.uuid4())
    sistem.aktif_oturum["paket_uuid_map"][barcode] = paket_uuid
    sistem.barkod_lojik = True
    
    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}")
    print(f"    └─ UUID: {paket_uuid}")
    
    veri_senkronizasyonu(barkod=barcode)
    log_oturum_var(f"Yeni ürün - Barkod: {barcode}, UUID: {paket_uuid}")

# ==================== GÖRÜNTÜ İŞLEME ====================

def goruntu_isleme_tetikle():
    """Görüntü işlemeyi tetikler"""
    try:
        goruntu_sonuc = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
        
        uzunluk_mm = float(goruntu_sonuc.genislik_mm)
        genislik_mm = float(goruntu_sonuc.yukseklik_mm)
        materyal = goruntu_sonuc.tur.value
        
        print(f"\n📷 [GÖRÜNTÜ İŞLEME] Sonuç alındı:")
        print(f"    ├─ Materyal Türü: {MATERYAL_ISIMLERI.get(materyal, 'BİLİNMEYEN')} ({materyal})")
        print(f"    ├─ Uzunluk: {uzunluk_mm} mm")
        print(f"    └─ Genişlik: {genislik_mm} mm")
        
        # Uzunluk verisini kuyruğa ekle
        sistem.uzunluk_goruntu_kuyruk.append(uzunluk_mm)
        print(f"📊 [UZUNLUK KUYRUK] Görüntü uzunluğu kuyruğa eklendi: {uzunluk_mm} mm (Kuyruk boyutu: {len(sistem.uzunluk_goruntu_kuyruk)})")
        
        veri_senkronizasyonu(
            materyal_turu=materyal,
            uzunluk=uzunluk_mm,
            genislik=genislik_mm
        )
        
        log_oturum_var(f"Görüntü işleme tamamlandı: {materyal}")
        
    except Exception as e:
        print(f"❌ [GÖRÜNTÜ İŞLEME HATA] {e}")
        log_error(f"Görüntü işleme hatası: {e}")
        sistem.iade_lojik = True
        sistem.iade_sebep = f"Görüntü işleme hatası: {str(e)}"

# ==================== VERİ SENKRONİZASYONU ====================

def veri_senkronizasyonu(barkod=None, agirlik=None, materyal_turu=None, uzunluk=None, genislik=None):
    """Thread-safe veri senkronizasyonu"""
    with veri_lock:
        # 1. YENİ ÜRÜN EKLEME
        if barkod is not None:
            sistem.veri_senkronizasyon_listesi.append({
                'barkod': barkod,
                'agirlik': None,
                'materyal_turu': None,
                'uzunluk': None,
                'genislik': None,
                'isleniyor': False
            })
            print(f"➕ [KUYRUK] Yeni ürün eklendi: {barkod} (Toplam: {len(sistem.veri_senkronizasyon_listesi)})")
            log_oturum_var(f"Kuyruk: Yeni ürün eklendi (Toplam: {len(sistem.veri_senkronizasyon_listesi)})")
            
            # Sadece barkod geldiyse çık
            if all(v is None for v in [agirlik, materyal_turu, uzunluk, genislik]):
                return
        
        # 2. HEDEF ÜRÜNÜ BUL
        target_urun = None
        for urun in reversed(sistem.veri_senkronizasyon_listesi):
            if not urun['isleniyor']:
                target_urun = urun
                break
        
        # 3. BARKODSUZ VERİ KONTROLÜ
        if target_urun is None and barkod is None:
            sebep = "Barkod bilgisi olmadan ürün verisi geldi"
            print(f"❌ [VERİ SENKRON HATA] {sebep}")
            log_error(sebep)
            sistem.iade_lojik = True
            sistem.iade_sebep = sebep
            dimdb_bildirim_gonder("BARKOD_YOK", agirlik or 0, materyal_turu or 0,
                                 uzunluk or 0, genislik or 0, False,
                                 AcceptPackageResultCodes.DIGER, sebep)
            return
        
        # 4. VERİ GÜNCELLEME
        if target_urun:
            guncellenen = []
            if agirlik is not None:
                target_urun['agirlik'] = agirlik
                guncellenen.append(f"Ağırlık: {agirlik}g")
            if materyal_turu is not None:
                target_urun['materyal_turu'] = materyal_turu
                guncellenen.append(f"Materyal: {materyal_turu}")
            if uzunluk is not None:
                target_urun['uzunluk'] = uzunluk
                guncellenen.append(f"Uzunluk: {uzunluk}mm")
            if genislik is not None:
                target_urun['genislik'] = genislik
                guncellenen.append(f"Genişlik: {genislik}mm")
            
            if guncellenen:
                print(f"✏️  [VERİ GÜNCELLEME] Barkod {target_urun.get('barkod')} için:")
                for item in guncellenen:
                    print(f"    └─ {item}")
        
        # 5. TAMAMLANMIŞ ÜRÜNLERİ İŞLE (FIFO - Sadece ilk ürün)
        for urun in sistem.veri_senkronizasyon_listesi:
            # Tüm veriler dolu mu?
            tum_veriler_dolu = all(deger is not None for anahtar, deger in urun.items() 
                                  if anahtar != 'isleniyor')
            
            if tum_veriler_dolu and not urun['isleniyor']:
                print(f"\n✅ [VERİ TAMAM] Tüm veriler alındı:")
                print(f"    ├─ Barkod: {urun['barkod']}")
                print(f"    ├─ Ağırlık: {urun['agirlik']}g")
                print(f"    ├─ Materyal: {MATERYAL_ISIMLERI.get(urun['materyal_turu'], 'BİLİNMEYEN')}")
                print(f"    ├─ Uzunluk: {urun['uzunluk']}mm")
                print(f"    └─ Genişlik: {urun['genislik']}mm")
                print(f"🔍 [DOĞRULAMA] İşlem başlatılıyor...")
                
                urun['isleniyor'] = True
                log_oturum_var(f"Doğrulama başlıyor: {urun['barkod']}")
                
                # Klape ayarı
                if urun['materyal_turu'] == 1:
                    sistem.motor_ref.klape_plastik()
                    print(f"🔧 [KLAPE] Plastik konumu ayarlandı")
                elif urun['materyal_turu'] == 3:
                    sistem.motor_ref.klape_metal()
                    print(f"🔧 [KLAPE] Metal konumu ayarlandı")
                
                # Doğrulama
                dogrulama(urun['barkod'], urun['agirlik'], urun['materyal_turu'],
                         urun['uzunluk'], urun['genislik'])
                
                # Kuyruktan çıkar
                sistem.veri_senkronizasyon_listesi.remove(urun)
                print(f"➖ [KUYRUK] Ürün işlendi ve kuyruktan çıkarıldı (Kalan: {len(sistem.veri_senkronizasyon_listesi)})")
                log_oturum_var(f"Ürün işlendi (Kalan: {len(sistem.veri_senkronizasyon_listesi)})")
                
                # Kuyruk boşsa barkod_lojik'i kapat
                if not sistem.veri_senkronizasyon_listesi:
                    sistem.barkod_lojik = False
                    print(f"🏁 [KUYRUK BOŞ] Yeni ürün kabul edilebilir")
                    log_oturum_var("Kuyruk boş - yeni ürün kabul edilebilir")
                
                break  # KRİTİK: Her çağrıda sadece 1 ürün işle (FIFO)

# ==================== DOĞRULAMA ====================

def dogrulama(barkod: str, agirlik: float, materyal_turu: int, 
              uzunluk: float, genislik: float):
    """Ürün doğrulama işlemi"""
    print(f"\n{'='*60}")
    print(f"🔍 [DOĞRULAMA BAŞLADI]")
    print(f"{'='*60}")
    print(f"Barkod: {barkod}")
    print(f"Ağırlık: {agirlik}g | Materyal: {MATERYAL_ISIMLERI.get(materyal_turu, 'BİLİNMEYEN')}")
    print(f"Uzunluk: {uzunluk}mm | Genişlik: {genislik}mm")
    
    log_oturum_var(f"Doğrulama başladı: {barkod} | {agirlik}g | Tür:{materyal_turu}")
    
    try:
        urun = veritabani_yoneticisi.barkodu_dogrula(barkod)
    except Exception as e:
        print(f"❌ [VERİTABANI HATASI] {e}")
        log_error(f"Veritabanı hatası: {e}")
        sistem.iade_lojik = True
        sistem.iade_sebep = "Veritabanı hatası"
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik,
                             False, AcceptPackageResultCodes.DIGER, "Veritabanı hatası")
        return
    
    if not urun:
        sebep = f"Ürün veritabanında yok (Barkod: {barkod})"
        print(f"❌ [DOĞRULAMA RED] {sebep}")
        log_error(sebep)
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik,
                             False, AcceptPackageResultCodes.TANIMA_HATASI, "Tanıma Hatası")
        return
    
    # Parametreleri al
    min_agirlik = urun.get('packMinWeight')
    max_agirlik = urun.get('packMaxWeight')
    min_genislik = urun.get('packMinWidth')
    max_genislik = urun.get('packMaxWidth')
    min_uzunluk = urun.get('packMinHeight')
    max_uzunluk = urun.get('packMaxHeight')
    materyal_id = urun.get('material')
    
    print(f"\n📊 [VERİTABANI LİMİTLERİ]")
    print(f"    Ağırlık: {min_agirlik}-{max_agirlik}g (Tolerans: ±{AGIRLIK_TOLERANSI}g)")
    print(f"    Genişlik: {min_genislik}-{max_genislik}mm (Tolerans: ±{GENISLIK_TOLERANSI}mm)")
    print(f"    Uzunluk: {min_uzunluk}-{max_uzunluk}mm (Tolerans: ±{UZUNLUK_TOLERANSI}mm)")
    print(f"    Materyal ID: {materyal_id}")
    
    # Ağırlık kontrolü
    agirlik_kabul = False
    if min_agirlik is None and max_agirlik is None:
        agirlik_kabul = True
    elif min_agirlik is not None and max_agirlik is not None:
        agirlik_kabul = (min_agirlik - AGIRLIK_TOLERANSI) <= agirlik <= (max_agirlik + AGIRLIK_TOLERANSI)
    elif min_agirlik is not None:
        agirlik_kabul = agirlik >= (min_agirlik - AGIRLIK_TOLERANSI)
    elif max_agirlik is not None:
        agirlik_kabul = agirlik <= (max_agirlik + AGIRLIK_TOLERANSI)
    
    if not agirlik_kabul:
        sebep = f"Ağırlık sınırları dışında ({agirlik}g)"
        print(f"❌ [AĞIRLIK RED] {sebep}")
        log_error(sebep)
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik,
                             False, AcceptPackageResultCodes.COK_AGIR, "Çok Ağır")
        return
    
    print(f"✅ [AĞIRLIK] Kontrol geçti: {agirlik}g")
    log_success(f"Ağırlık kontrolü geçti: {agirlik}g")
    
    # Genişlik kontrolü
    if not ((min_genislik - GENISLIK_TOLERANSI) <= genislik <= (max_genislik + GENISLIK_TOLERANSI)):
        sebep = f"Genişlik sınırları dışında ({genislik}mm)"
        print(f"❌ [GENİŞLİK RED] {sebep}")
        log_error(sebep)
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik,
                             False, AcceptPackageResultCodes.GENIS_PROFIL_UYGUN_DEGIL, 
                             "Geniş profil uygun değil")
        return
    
    print(f"✅ [GENİŞLİK] Kontrol geçti: {genislik}mm")
    log_success(f"Genişlik kontrolü geçti: {genislik}mm")
    
    # Uzunluk kontrolü
    if not ((min_uzunluk - UZUNLUK_TOLERANSI) <= uzunluk <= (max_uzunluk + UZUNLUK_TOLERANSI)):
        sebep = f"Uzunluk sınırları dışında ({uzunluk}mm)"
        print(f"❌ [UZUNLUK RED] {sebep}")
        log_error(sebep)
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik,
                             False, AcceptPackageResultCodes.YUKSEKLIK_UYGUN_DEGIL, 
                             "Yükseklik uygun değil")
        return
    
    print(f"✅ [UZUNLUK] Kontrol geçti: {uzunluk}mm")
    log_success(f"Uzunluk kontrolü geçti: {uzunluk}mm")
    
    # Materyal kontrolü
    if materyal_id != materyal_turu:
        sebep = f"Materyal türü uyuşmuyor (Beklenen: {materyal_id}, Gelen: {materyal_turu})"
        print(f"❌ [MATERYAL RED] {sebep}")
        log_error(sebep)
        sistem.iade_lojik = True
        sistem.iade_sebep = sebep
        dimdb_bildirim_gonder(barkod, agirlik, materyal_turu, uzunluk, genislik,
                             False, AcceptPackageResultCodes.CESITLI_RED, "Çeşitli Red")
        return
    
    print(f"✅ [MATERYAL] Kontrol geçti: {MATERYAL_ISIMLERI.get(materyal_turu, 'BİLİNMEYEN')}")
    log_success(f"Materyal türü kontrolü geçti: {materyal_turu}")
    
    # Başarılı - ürünü kabul et
    kabul_edilen_urun = {
        'barkod': barkod,
        'agirlik': agirlik,
        'materyal_turu': materyal_turu,
        'uzunluk': uzunluk,
        'genislik': genislik
    }
    
    sistem.kabul_edilen_urunler.append(kabul_edilen_urun)
    sistem.onaylanan_urunler.append(kabul_edilen_urun.copy())
    
    print(f"\n{'='*60}")
    print(f"✅ [ÜRÜN KABUL EDİLDİ] {barkod}")
    print(f"{'='*60}")
    print(f"📦 Kabul Edilen Ürün Kuyruğu: {len(sistem.kabul_edilen_urunler)} ürün")
    print(f"{'='*60}\n")
    
    log_success(f"Ürün kabul edildi: {barkod} (Kuyruk: {len(sistem.kabul_edilen_urunler)})")

# ==================== MANUEL KONTROLLER ====================

def manuel_ezici_kontrol(komut: str) -> bool:
    """Manuel ezici kontrolü"""
    if not sistem.motor_kontrol_ref:
        return False
    
    try:
        komut_map = {
            "ileri": sistem.motor_kontrol_ref.ezici_ileri,
            "geri": sistem.motor_kontrol_ref.ezici_geri,
            "dur": sistem.motor_kontrol_ref.ezici_dur,
            "ileri_10sn": sistem.motor_kontrol_ref.ezici_ileri_10sn,
            "geri_10sn": sistem.motor_kontrol_ref.ezici_geri_10sn
        }
        fonksiyon = komut_map.get(komut)
        return fonksiyon() if fonksiyon else False
    except Exception as e:
        log_error(f"Manuel ezici hatası: {e}")
        return False

def manuel_kirici_kontrol(komut: str) -> bool:
    """Manuel kırıcı kontrolü"""
    if not sistem.motor_kontrol_ref:
        return False
    
    try:
        komut_map = {
            "ileri": sistem.motor_kontrol_ref.kirici_ileri,
            "geri": sistem.motor_kontrol_ref.kirici_geri,
            "dur": sistem.motor_kontrol_ref.kirici_dur,
            "ileri_10sn": sistem.motor_kontrol_ref.kirici_ileri_10sn,
            "geri_10sn": sistem.motor_kontrol_ref.kirici_geri_10sn
        }
        fonksiyon = komut_map.get(komut)
        return fonksiyon() if fonksiyon else False
    except Exception as e:
        log_error(f"Manuel kırıcı hatası: {e}")
        return False

# ==================== YÖNLENDİRME ====================

def uzunluk_dogrulama(motor_uzunluk: float, goruntu_uzunluk: float) -> bool:
    """Motor ve görüntü uzunluk verilerini karşılaştırır"""
    if motor_uzunluk is None or goruntu_uzunluk is None:
        print(f"❌ [UZUNLUK DOĞRULAMA HATA] Verilerden biri None")
        print(f"    ├─ Motor: {motor_uzunluk}")
        print(f"    └─ Görüntü: {goruntu_uzunluk}")
        log_error("Uzunluk doğrulama: Verilerden biri None")
        return False
    
    sonuc = ((goruntu_uzunluk - UZUNLUK_DOGRULAMA_TOLERANSI) <= 
             motor_uzunluk <= 
             (goruntu_uzunluk + UZUNLUK_DOGRULAMA_TOLERANSI))
    
    if sonuc:
        print(f"✅ [UZUNLUK DOĞRULAMA] Başarılı")
        print(f"    ├─ Motor Uzunluk: {motor_uzunluk:.2f} mm")
        print(f"    ├─ Görüntü Uzunluk: {goruntu_uzunluk:.2f} mm")
        print(f"    ├─ Fark: {abs(motor_uzunluk - goruntu_uzunluk):.2f} mm")
        print(f"    └─ Tolerans: ±{UZUNLUK_DOGRULAMA_TOLERANSI} mm")
        log_success(f"Uzunluk doğrulandı: Motor={motor_uzunluk}mm, Görüntü={goruntu_uzunluk}mm")
    else:
        print(f"❌ [UZUNLUK DOĞRULAMA] Uyuşmazlık!")
        print(f"    ├─ Motor Uzunluk: {motor_uzunluk:.2f} mm")
        print(f"    ├─ Görüntü Uzunluk: {goruntu_uzunluk:.2f} mm")
        print(f"    ├─ Fark: {abs(motor_uzunluk - goruntu_uzunluk):.2f} mm")
        print(f"    └─ Tolerans: ±{UZUNLUK_DOGRULAMA_TOLERANSI} mm (AŞILDI!)")
        log_error(f"Uzunluk uyuşmazlığı: Motor={motor_uzunluk}mm, Görüntü={goruntu_uzunluk}mm")
    
    return sonuc

def yonlendirici_hareket():
    """Ürünü yönlendirir"""
    print(f"\n{'='*60}")
    print(f"🔄 [YÖNLENDİRME BAŞLADI]")
    print(f"{'='*60}")
    
    if not sistem.kabul_edilen_urunler:
        print(f"⚠️ [YÖNLENDİRME HATA] Kabul edilen ürün kuyruğu boş!")
        log_warning("Yönlendirme: Kuyruk boş")
        sistem.motor_ref.konveyor_geri()
        sistem.iade_lojik = True
        sistem.iade_sebep = "Yönlendirme için ürün yok"
        sistem_temizle()
        return
    
    # Motor uzunluk ölçümünü tetikle
    sistem.motor_ref.atik_uzunluk()
    time.sleep(UZUNLUK_OLCUM_BEKLEME)
    
    # Uzunluk verisini timeout ile bekle (maksimum 2 saniye)
    max_bekle = 2.0  # saniye
    bekleme_araligi = 0.01  # 10ms
    toplam_bekleme = 0
    
    while sistem.uzunluk_motor_verisi is None and toplam_bekleme < max_bekle:
        time.sleep(bekleme_araligi)
        toplam_bekleme += bekleme_araligi
    
    motor_uzunluk = sistem.uzunluk_motor_verisi
    sistem.uzunluk_motor_verisi = None  # Kullanıldı, temizle
    
    print(f"📏 [MOTOR UZUNLUK] Ölçüm alındı: {motor_uzunluk} mm (Bekleme: {toplam_bekleme*1000:.0f}ms)")
    
    if motor_uzunluk is None:
        print(f"❌ [YÖNLENDİRME HATA] Motor uzunluk verisi alınamadı (Timeout: {max_bekle}s)!")
        log_error("Uzunluk verisi alınamadı - timeout")
        sistem.iade_lojik = True
        sistem.iade_sebep = "Uzunluk verisi alınamadı"
        sistem_temizle()
        return
    
    # Görüntü uzunluğunu kuyruktan al (FIFO)
    if not sistem.uzunluk_goruntu_kuyruk:
        print(f"❌ [YÖNLENDİRME HATA] Görüntü uzunluk kuyruğu boş!")
        log_error("Görüntü uzunluk kuyruğu boş")
        sistem.iade_lojik = True
        sistem.iade_sebep = "Görüntü uzunluk verisi yok"
        sistem_temizle()
        return
    
    goruntu_uzunluk = sistem.uzunluk_goruntu_kuyruk.popleft()
    print(f"📷 [GÖRÜNTÜ UZUNLUK] Kuyruktan alındı: {goruntu_uzunluk} mm")
    print(f"📊 [UZUNLUK KUYRUK] Kalan görüntü uzunluk: {len(sistem.uzunluk_goruntu_kuyruk)}")
    
    # Uzunluk doğrulama
    if not uzunluk_dogrulama(motor_uzunluk, goruntu_uzunluk):
        print(f"❌ [YÖNLENDİRME HATA] Uzunluk uyuşmazlığı!")
        sistem.iade_lojik = True
        sistem.iade_sebep = "Uzunluk uyuşmazlığı"
        sistem_temizle()
        return
    
    # Ürünü yönlendir
    urun = sistem.kabul_edilen_urunler[0]
    sistem.son_islenen_urun = urun.copy()
    materyal_id = urun['materyal_turu']
    materyal_adi = MATERYAL_ISIMLERI.get(materyal_id, "BİLİNMEYEN")
    
    print(f"\n📦 [İŞLENECEK ÜRÜN]")
    print(f"    ├─ Barkod: {urun['barkod']}")
    print(f"    ├─ Materyal: {materyal_adi} ({materyal_id})")
    print(f"    ├─ Ağırlık: {urun['agirlik']}g")
    print(f"    └─ Boyut: {urun['uzunluk']}x{urun['genislik']} mm")
    
    log_oturum_var(f"Yönlendirme: {materyal_adi} - {urun['barkod']}")
    
    sistem.yonlendirici_calisiyor = True
    print(f"⏸️  [KONVEYÖR] Durduruldu")
    
    if materyal_id == 2:  # Cam
        if sistem.kirici_durum:
            print(f"🔨 [KIRICI] 10 saniye ileri başlatıldı")
            manuel_kirici_kontrol("ileri_10sn")
        sistem.motor_ref.yonlendirici_cam()
        print(f"🟦 [CAM] Cam yönlendiricisine gönderildi")
        log_oturum_var("Cam yönlendiricisine gönderildi")
    else:  # Plastik/Metal
        if sistem.ezici_durum:
            print(f"💥 [EZİCİ] 10 saniye ileri başlatıldı")
            manuel_ezici_kontrol("ileri_10sn")
        sistem.motor_ref.yonlendirici_plastik()
        print(f"🟩 [{materyal_adi}] Plastik/Metal yönlendiricisine gönderildi")
        log_oturum_var(f"{materyal_adi} yönlendiricisine gönderildi")
    
    
    sistem.kabul_edilen_urunler.popleft()
    
    print(f"✅ [YÖNLENDİRME TAMAMLANDI]")
    print(f"    └─ Kalan ürün: {len(sistem.kabul_edilen_urunler)}")
    print(f"{'='*60}\n")
    
    log_oturum_var(f"Yönlendirme tamamlandı (Kalan: {len(sistem.kabul_edilen_urunler)})")

# ==================== LOJİK YÖNETİCİSİ ====================

def lojik_yoneticisi():
    """Ana sistem lojik döngüsü"""
    print(f"\n{'#'*60}")
    print(f"🚀 LOJİK YÖNETİCİSİ BAŞLATILDI")
    print(f"{'#'*60}\n")
    log_system("Lojik yöneticisi başlatıldı")
    
    while sistem.sistem_calisma_durumu:
        time.sleep(LOJIK_DONGU_BEKLEME)
        
        try:
            # GSI - Giriş Sensörü İçeri
            if sistem.gsi_lojik:
                sistem.gsi_lojik = False
                
                # UPS kesintisi sonrası GSI kontrolü
                from ...api.servisler.ups_power_handlers import check_gsi_after_power_restore
                if check_gsi_after_power_restore():
                    continue  # UPS kesintisi sonrası GSI işlendi, döngüye devam et
                
                sistem.giris_sensor_durum = True
                sistem.gsi_gecis_lojik = True
                
                if sistem.iade_lojik:
                    print(f"🚫 [GSI] İade aktif - Ürünü alınız")
                    log_warning("GSI: İade aktif - Ürünü alınız")
                    time.sleep(0.25)
                    sistem.motor_ref.konveyor_dur()
                else:
                    print(f"▶️  [GSI] Konveyör ileri başlatıldı")
                    log_oturum_var("GSI: Konveyör ileri")
                    sistem.motor_ref.konveyor_ileri()
            
            # YSO - Yönlendirici Sensörü Oturum
            if sistem.yso_lojik:
                sistem.yso_lojik = False
                print(f"\n🎯 [YSO] Yönlendirme noktası tetiklendi")
                log_oturum_var("YSO: Yönlendirme başlatıldı")
                sistem.motor_ref.konveyor_dur()
                yonlendirici_hareket()
            
            '''# Yönlendirici sahtecilik kontrolü
            if sistem.yonlendirici_calisiyor and (sistem.ysi_lojik or sistem.yso_lojik):
                sistem.son_islenen_urun = None
                sistem.motor_ref.yonlendirici_dur()
                print(f"🚨 [SAHTECİLİK] Yönlendiriciden geri çekilme algılandı!")
                log_error("SAHTECİLİK: Yönlendiriciden geri çekildi")
                sistem.iade_lojik = True
                sistem.iade_sebep = "Sahtecilik algılandı"
                sistem_temizle()

            '''
            
            # YMK - Yönlendirici Motor Konumda
            if sistem.yonlendirici_konumda:
                sistem.yonlendirici_konumda = False
                sistem.yonlendirici_calisiyor = False
                if sistem.agirlik_kuyruk:
                    cikartilan_agirlik = sistem.agirlik_kuyruk.popleft()
                    print(f"⚖️ [AĞIRLIK KUYRUK] Çıkartıldı: {cikartilan_agirlik:.2f}g (Kalan: {len(sistem.agirlik_kuyruk)})")
                print(f"🎯 [YMK] Yönlendirici konuma ulaştı")
                
                # DİM-DB bildirimi
                if sistem.son_islenen_urun:
                    urun = sistem.son_islenen_urun
                    print(f"📡 [DİM-DB] Başarılı bildirim gönderiliyor: {urun['barkod']}")
                    dimdb_bildirim_gonder(
                        urun['barkod'], urun['agirlik'], urun['materyal_turu'],
                        urun['uzunluk'], urun['genislik'], True,
                        AcceptPackageResultCodes.BASARILI, "Başarılı"
                    )
                    sistem.son_islenen_urun = None
                
                # Konveyör kontrolü
                if sistem.veri_senkronizasyon_listesi or sistem.kabul_edilen_urunler:
                    print(f"▶️  [YMK] Konveyör ileri - Bekleyen ürün var")
                    log_oturum_var("YMK: Konveyör ileri - ürün var")
                    sistem.motor_ref.konveyor_ileri()
                else:
                    if sistem.gsi_gecis_lojik and not sistem.iade_lojik:
                        print(f"▶️  [YMK] Konveyör ileri - GSI geçiş aktif")
                        log_oturum_var("YMK: Konveyör ileri - gsi_gecis_lojik aktif")
                        sistem.motor_ref.konveyor_ileri()
                    else:
                        print(f"⏸️  [YMK] Konveyör durduruldu")
                        log_oturum_var("YMK: Konveyör dur")
                        sistem.motor_ref.konveyor_dur()
                        sistem.gsi_gecis_lojik = False
            
            # Ağırlık işleme
            if sistem.agirlik is not None:
                if sistem.barkod_lojik and not sistem.iade_lojik:
                    # Konveyördeki toplam ağırlığı hesapla
                    toplam_konveyor_agirligi = sum(sistem.agirlik_kuyruk) if sistem.agirlik_kuyruk else 0
                    gercek_agirlik = sistem.agirlik - toplam_konveyor_agirligi
                    
                    print(f"\n⚖️  [AĞIRLIK ÖLÇÜMÜ]")
                    print(f"    ├─ Toplam Ölçülen: {sistem.agirlik:.2f}g")
                    if toplam_konveyor_agirligi > 0:
                        print(f"    ├─ Konveyördeki: {toplam_konveyor_agirligi:.2f}g")
                    print(f"    └─ Gerçek Ağırlık: {gercek_agirlik:.2f}g")
                    
                    log_oturum_var(f"Ağırlık: Ölçülen={sistem.agirlik:.2f}g, Konveyör={toplam_konveyor_agirligi:.2f}g, Gerçek={gercek_agirlik:.2f}g")
                    
                    sistem.agirlik_kuyruk.append(gercek_agirlik)
                    print(f"📊 [AĞIRLIK KUYRUK] Eklendi (Toplam: {len(sistem.agirlik_kuyruk)})")
                    veri_senkronizasyonu(agirlik=gercek_agirlik)
                else:
                    print(f"⚠️ [AĞIRLIK] Ölçüm yapıldı ama işlenemedi: {sistem.agirlik:.2f}g")
                    print(f"    ├─ barkod_lojik: {sistem.barkod_lojik}")
                    print(f"    └─ iade_lojik: {sistem.iade_lojik}")
                    log_warning(f"Ağırlık ölçüldü ama işlenemedi: {sistem.agirlik:.2f}g")
                
                sistem.agirlik = None
            
            # İade lojik
            if sistem.iade_lojik:
                if not sistem.kabul_edilen_urunler and not sistem.veri_senkronizasyon_listesi:
                    if not sistem.iade_etildi:
                        giris_iade_et(sistem.iade_sebep)
                        sistem.iade_sebep = None
                        sistem.iade_etildi = True
            else:
                sistem.iade_etildi = False
            
            # Konveyör durum kontrolü
            if (not sistem.kabul_edilen_urunler and 
                not sistem.veri_senkronizasyon_listesi and 
                not sistem.iade_lojik):
                if not sistem.konveyor_durum_kontrol:
                    print(f"💤 [KONVEYÖR] Durduruldu - Sistem boş")
                    log_system("Konveyör durduruldu - sistem boş")
                    sistem.motor_ref.konveyor_dur()
                    sistem.konveyor_durum_kontrol = True
            elif sistem.konveyor_durum_kontrol:
                sistem.konveyor_durum_kontrol = False
            
            # Konveyör adım problemi
            if sistem.konveyor_adim_problem:
                sistem.konveyor_adim_problem = False
                print(f"⚠️ [KONVEYÖR PROBLEM] Adım problemi algılandı")
                
                if (not sistem.kabul_edilen_urunler and 
                    not sistem.veri_senkronizasyon_listesi):
                    
                    if not sistem.iade_lojik:
                        print(f"🔧 [KONVEYÖR] Problem var sinyali gönderiliyor")
                        log_error("Konveyör adım problemi - sistem boş")
                        sistem.motor_ref.konveyor_problem_var()
                    else:
                        # Görüntü kontrolü
                        print(f"📷 [KONVEYÖR] Şişe alındı mı kontrol ediliyor...")
                        goruntu = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
                        if goruntu.mesaj == "nesne_yok":
                            print(f"✅ [KONVEYÖR] Problem çözüldü - Şişe alındı")
                            log_success("Konveyör problemi çözüldü - şişe alındı")
                            sistem.iade_lojik = False
                            sistem.barkod_lojik = False
                            sistem_temizle()
                            uyari.uyari_kapat()
                        else:
                            print(f"⚠️ [KONVEYÖR] Problem devam ediyor")
                            log_warning("Konveyör problemi devam ediyor")
                            sistem.iade_lojik = True
                else:
                    print(f"ℹ️  [KONVEYÖR] Problem yok - Sistem meşgul")
                    log_warning("Konveyör adım problemi - sistem boş değil")
                    sistem.motor_ref.konveyor_problem_yok()
            
            # GSO - Giriş Sensörü Oturum
            if sistem.gso_lojik:
                sistem.gso_lojik = False
                sistem.giris_sensor_durum = False
                print(f"\n🚪 [GSO] Giriş sensörü çıkış tetiklendi")
                
                if sistem.iade_lojik:
                    # Görüntü kontrolü - şişe alındı mı?
                    print(f"📷 [GSO] Şişe alındı mı kontrol ediliyor...")
                    goruntu = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
                    if goruntu.mesaj == "nesne_yok":
                        print(f"✅ [GSO] Şişe alındı - İade tamamlandı")
                        log_success("GSO: Şişe alındı")
                        sistem.iade_lojik = False
                        sistem.barkod_lojik = False
                        sistem_temizle()
                        uyari.uyari_kapat()
                    else:
                        print(f"◀️  [GSO] Şişe alınmadı - Geri dönüyor")
                        log_warning("GSO: Şişe alınmadı - geri dönüyor")
                        sistem.kabul_yonu = False
                        sistem.motor_ref.konveyor_geri()
                else:
                    if sistem.barkod_lojik:
                        if not sistem.iade_lojik:
                            print(f"📷 [GSO] Görüntü işleme başlatılıyor...")
                            log_oturum_var("GSO: Görüntü işleme başlatılıyor")
                            sistem.kabul_yonu = True
                            sistem.sensor_ref.loadcell_olc()
                            goruntu_isleme_tetikle()
                            sistem.gsi_gecis_lojik = False
                    else:
                        print(f"❌ [GSO] Barkod okunmadı - İade başlatılıyor")
                        log_error("GSO: Barkod okunmadı - iade")
                        sistem.iade_lojik = True
                        sistem.iade_sebep = "Barkod okunmadı"
            
            # YSI - Yönlendirici Sensörü İçeri
            if sistem.ysi_lojik:
                sistem.ysi_lojik = False
                print(f"🎯 [YSI] Yönlendirici giriş sensörü tetiklendi")
                log_oturum_var("YSI tetiklendi")
        
        except Exception as e:
            print(f"\n❌ [LOJİK YÖNETİCİSİ HATA] {e}")
            print(f"    └─ Sistem güvenli moda alınıyor...")
            log_error(f"Lojik yöneticisi hatası: {e}")
            sistem.iade_lojik = True
            sistem.iade_sebep = f"Sistem hatası: {str(e)}"
    
    print(f"\n{'#'*60}")
    print(f"🛑 LOJİK YÖNETİCİSİ DURDURULDU")
    print(f"{'#'*60}\n")
    log_system("Lojik yöneticisi durduruldu")

# ==================== İADE YÖNETİMİ ====================

def giris_iade_et(sebep: str):
    """Ürünü iade et"""
    print(f"\n{'='*60}")
    print(f"🔙 [İADE] Ürün iade ediliyor")
    print(f"{'='*60}")
    print(f"Sebep: {sebep}")
    print(f"{'='*60}\n")
    uyari.uyari_goster(mesaj=f"Lütfen şişeyi geri alınız : {sebep}", sure=0)
    log_error(f"Giriş iadesi: {sebep}")
    sistem.kabul_yonu = False
    sistem.motor_ref.konveyor_geri()
    print(f"◀️  [KONVEYÖR] Geri yönde başlatıldı")

# ==================== MESAJ İŞLEME ====================

def mesaj_isle(mesaj: str):
    """Gelen mesajları işler"""
    mesaj = mesaj.strip().lower()
    
    # Oturum başlatma
    if mesaj == "oturum_var":
        # Port sağlık servisini durdur
        from .. import kart_referanslari
        port_saglik = kart_referanslari.port_saglik_servisi_al()
        if port_saglik:
            port_saglik.oturum_durumu_guncelle(oturum_var=True)
            log_system("Port sağlık servisi duraklatıldı - Oturum aktif")
        
        if not sistem.lojik_thread_basladi:
            print(f"\n{'*'*60}")
            print(f"🟢 OTURUM BAŞLATILIYOR")
            print(f"{'*'*60}\n")
            log_oturum_var("Aktif oturum başlatıldı - Lojik thread başlatılıyor")
            t1 = threading.Thread(target=lojik_yoneticisi, daemon=True, name="LojikYoneticisi")
            t1.start()
            sistem.lojik_thread_basladi = True
        else:
            print(f"⚠️ [OTURUM] Lojik yöneticisi zaten çalışıyor")
            log_warning("Lojik yöneticisi zaten çalışıyor")
        
        # Sistem sıfırlama
        print(f"🔄 [SİSTEM SIFIRLAMA] Başlatılıyor...")
        sistem.iade_lojik = False
        sistem.iade_lojik_onceki_durum = False
        sistem.barkod_lojik = False
        sistem_temizle()
        sistem.onaylanan_urunler.clear()
        sistem.uzunluk_motor_verisi = None
        sistem.ezici_durum = True
        sistem.kirici_durum = True
        
        # UUID map temizle
        sistem.aktif_oturum["paket_uuid_map"].clear()
        print(f"✅ [SİSTEM SIFIRLAMA] Tamamlandı")
        
        # Motorları başlat
        print(f"🔧 [MOTOR BAŞLATMA] Motorlar aktif ediliyor...")
        sistem.iade_lojik = True
        sistem.sensor_ref.makine_oturum_var()
        sistem.motor_ref.motorlari_aktif_et()
        sistem.motor_ref.konveyor_geri()
        print(f"⚖️ [SENSOR] Tare işlemi başlatılıyor...")
        sistem.sensor_ref.tare()
        sistem.sensor_ref.led_ac()
        
        print(f"⏳ [BEKLEME] {OTURUM_BASLANGIC_BEKLEME} saniye bekleniyor...")
        time.sleep(OTURUM_BASLANGIC_BEKLEME)
        sistem.motor_ref.konveyor_dur()
        sistem.kabul_yonu = True
        sistem.iade_lojik = False
        print(f"\n{'*'*60}")
        print(f"✅ OTURUM HAZIR - Ürün kabul edilebilir")
        print(f"{'*'*60}\n")
        log_success("Oturum hazır")
        return
    
    # Ağırlık verisi
    if mesaj.startswith("a:"):
        try:
            sistem.agirlik = float(mesaj.split(":")[1].replace(",", "."))
        except (ValueError, IndexError) as e:
            print(f"❌ [AĞIRLIK PARSE HATA] {e}")
            log_error(f"Ağırlık verisi hatası: {e}")
        return
    
    # Motor uzunluk verisi
    if mesaj.startswith("m:"):
        try:
            sistem.uzunluk_motor_verisi = float(mesaj.split(":")[1].replace(",", "."))
        except (ValueError, IndexError) as e:
            print(f"❌ [MOTOR UZUNLUK PARSE HATA] {e}")
            log_error(f"Motor uzunluk verisi hatası: {e}")
        return
    
    # Sensör ve durum mesajları
    mesaj_map = {
        "gsi": lambda: setattr(sistem, 'gsi_lojik', True),
        "gso": lambda: setattr(sistem, 'gso_lojik', True),
        "yso": lambda: setattr(sistem, 'yso_lojik', True),
        "ysi": lambda: setattr(sistem, 'ysi_lojik', True),
        "kma": lambda: setattr(sistem, 'konveyor_alarm', True),
        "yma": lambda: setattr(sistem, 'yonlendirici_alarm', True),
        "sma": lambda: setattr(sistem, 'seperator_alarm', True),
        "kmk": lambda: setattr(sistem, 'konveyor_konumda', True),
        "ymk": lambda: setattr(sistem, 'yonlendirici_konumda', True),
        "smk": lambda: setattr(sistem, 'seperator_konumda', True),
        "kmh": lambda: setattr(sistem, 'konveyor_hata', True),
        "ymh": lambda: setattr(sistem, 'yonlendirici_hata', True),
        "smh": lambda: setattr(sistem, 'seperator_hata', True),
        "kmp": lambda: setattr(sistem, 'konveyor_adim_problem', True),
        "ykt": lambda: setattr(sistem, 'yonlendirici_kalibrasyon', True),
        "skt": lambda: setattr(sistem, 'seperator_kalibrasyon', True),
    }
    
    handler = mesaj_map.get(mesaj)
    if handler:
        handler()

def modbus_mesaj(modbus_verisi):
    """Modbus verilerini işler"""
    pass

def sistem_kapat():
    """Sistemi temiz bir şekilde kapatır"""
    print(f"\n{'!'*60}")
    print(f"🛑 SİSTEM KAPATILIYOR")
    print(f"{'!'*60}\n")
    log_system("Sistem kapatılıyor...")
    sistem.sistem_calisma_durumu = False
    time.sleep(0.1)
    
    # Port sağlık servisini başlat
    from .. import kart_referanslari
    port_saglik = kart_referanslari.port_saglik_servisi_al()
    if port_saglik:
        port_saglik.oturum_durumu_guncelle(oturum_var=False)
        log_system("Port sağlık servisi devam ediyor - Oturum kapandı")
    
    print(f"✅ Sistem güvenli bir şekilde kapatıldı\n")
    log_success("Sistem güvenli bir şekilde kapatıldı")