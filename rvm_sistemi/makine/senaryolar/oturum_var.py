import time
from collections import deque
from ...veri_tabani import veritabani_yoneticisi
import threading
from ..goruntu.goruntu_isleme_servisi import GoruntuIslemeServisi
import uuid as uuid_lib
from dataclasses import dataclass, field
from . import uyari
from ...utils.logger import log_oturum_var, log_error, log_success, log_warning, log_system

@dataclass
class SistemDurumu:
    # Referanslar
    motor_ref: object = None
    sensor_ref: object = None
    motor_kontrol_ref: object = None  # GA500 motor kontrol referansı

    # Veriler
    agirlik: float = None
    uzunluk_motor_verisi: float = None

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
    iade_lojik: bool = False
    iade_lojik_onceki_durum: bool = False
    barkod_lojik: bool = False
    gsi_lojik: bool = False
    gsi_gecis_lojik: bool = False
    giris_sensor_durum: bool = False
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
    if sistem.iade_lojik:
        print(f"🚫 [İADE AKTIF] Barkod görmezden gelindi: {barcode}")
        log_oturum_var(f"İADE AKTIF - Barkod görmezden gelindi: {barcode}")
        return

    if sistem.barkod_lojik: # Kuyruğa bir limit koymak iyi olabilir
        print(f"⚠️ [BARKOD] Kuyruk dolu, yeni barkod görmezden gelindi: {barcode}")
        log_warning(f"BARKOD - Kuyruk dolu, yeni barkod görmezden gelindi: {barcode}")
        return

    paket_uuid = str(uuid_lib.uuid4())
    sistem.aktif_oturum["paket_uuid_map"][barcode] = paket_uuid
    sistem.barkod_lojik = True # Sistemin en az bir ürün beklediğini belirtir.
    
    veri_senkronizasyonu(barkod=barcode)
    print(f"\n📋 [YENİ ÜRÜN] Barkod okundu: {barcode}, UUID: {paket_uuid}")
    log_oturum_var(f"YENİ ÜRÜN - Barkod okundu: {barcode}, UUID: {paket_uuid}")

def goruntu_isleme_tetikle():
    """Görüntü işlemeyi tetikler ve sonuçları veri senkronizasyonuna gönderir"""
    goruntu_sonuc = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
    print(f"\n📷 [GÖRÜNTÜ İŞLEME] Sonuç: {goruntu_sonuc}")
    log_oturum_var(f"GÖRÜNTÜ İŞLEME - Sonuç: {goruntu_sonuc}")
    
    veri_senkronizasyonu(
        materyal_turu=goruntu_sonuc.tur.value, 
        uzunluk=float(goruntu_sonuc.genislik_mm), 
        genislik=float(goruntu_sonuc.yukseklik_mm)
    )

def veri_senkronizasyonu(barkod=None, agirlik=None, materyal_turu=None, uzunluk=None, genislik=None):
    with veri_lock: # Bu blok içindeki kodun aynı anda sadece bir thread tarafından çalıştırılmasını sağlar
        
        # 1. YENİ ÜRÜN EKLEME (Sadece barkod gelirse)
        if barkod is not None:
            sistem.veri_senkronizasyon_listesi.append({
                'barkod': barkod,
                'agirlik': None,
                'materyal_turu': None,
                'uzunluk': None,
                'genislik': None,
                'isleniyor': False # Ürünün işleme alınıp alınmadığını takip eden bayrak
            })
            print(f"➕ [KUYRUK] Yeni ürün eklendi: {barkod}. Kuyruk boyutu: {len(sistem.veri_senkronizasyon_listesi)}")
            log_oturum_var(f"KUYRUK - Yeni ürün eklendi: {barkod}. Kuyruk boyutu: {len(sistem.veri_senkronizasyon_listesi)}")
            # Eğer sadece barkod geldiyse, diğer verileri bekle, hemen çık.
            if all(v is None for v in [agirlik, materyal_turu, uzunluk, genislik]):
                return

        # 2. MEVCUT ÜRÜNÜ GÜNCELLEME
        target_urun = None
        # Kuyrukta sondan başa doğru giderek verisi eksik olan en yeni ürünü bul
        for urun in reversed(sistem.veri_senkronizasyon_listesi):
            if not urun['isleniyor']:
                target_urun = urun
                break
        
        # Eğer barkodsuz bir veri geldiyse ve atanacak bir ürün yoksa, bu bir hatadır.
        if target_urun is None and barkod is None:
            sebep = "Barkod bilgisi olmadan ürün verisi (ağırlık vb.) geldi."
            print(f"❌ [HATA] {sebep}")
            log_error(f"HATA - {sebep}")
            sistem.iade_lojik = True
            sistem.iade_sebep = sebep
            dimdb_bildirim_gonder("BARKOD_YOK", agirlik or 0, materyal_turu or 0, uzunluk or 0, genislik or 0, False, 6, sebep)
            return

        # Gelen verileri hedef ürüne ata
        if target_urun:
            if agirlik is not None: target_urun['agirlik'] = agirlik
            if materyal_turu is not None: target_urun['materyal_turu'] = materyal_turu
            if uzunluk is not None: target_urun['uzunluk'] = uzunluk
            if genislik is not None: target_urun['genislik'] = genislik
            print(f"✏️  [GÜNCELLEME] Barkod {target_urun.get('barkod')} için veri güncellendi.")
            log_oturum_var(f"GÜNCELLEME - Barkod {target_urun.get('barkod')} için veri güncellendi.")

        # 3. İŞLEME (Verisi Tamamlanmış Ürünleri Kontrol Et)
        for urun in sistem.veri_senkronizasyon_listesi:
            tum_veriler_dolu = all(deger is not None for anahtar, deger in urun.items() if anahtar != 'isleniyor')
            
            if tum_veriler_dolu and not urun['isleniyor']:
                print(f"✅ [VERİ SENKRONİZASYONU] Tüm veriler alındı, doğrulama başlıyor: {urun['barkod']}")
                log_oturum_var(f"VERİ SENKRONİZASYONU - Tüm veriler alındı, doğrulama başlıyor: {urun['barkod']}")
                urun['isleniyor'] = True # Tekrar işleme alınmasını engelle
                
                # Motor kontrolü (Klape Ayarı)
                if urun['materyal_turu'] == 1: sistem.motor_ref.klape_plastik()
                elif urun['materyal_turu'] == 3: sistem.motor_ref.klape_metal()
                
                # Doğrulama fonksiyonu çağırılıyor.
                dogrulama(urun['barkod'], urun['agirlik'], urun['materyal_turu'], urun['uzunluk'], urun['genislik'])  
                
                # İşlenen ürünü kuyruktan kaldır.
                sistem.veri_senkronizasyon_listesi.remove(urun)
                print(f"➖ [KUYRUK] Ürün işlendi ve kuyruktan çıkarıldı: {urun['barkod']}. Kalan: {len(sistem.veri_senkronizasyon_listesi)}")
                log_oturum_var(f"KUYRUK - Ürün işlendi ve kuyruktan çıkarıldı: {urun['barkod']}. Kalan: {len(sistem.veri_senkronizasyon_listesi)}")

                # Eğer kuyrukta başka ürün kalmadıysa barkod_lojik'i kapat.
                if not sistem.veri_senkronizasyon_listesi:
                    sistem.barkod_lojik = False
                    print("🏁 [KUYRUK] İşlenecek başka ürün kalmadı.")
                    log_oturum_var("KUYRUK - İşlenecek başka ürün kalmadı.")
                break # Her çağrıda sadece bir ürünü işle, FIFO mantığını koru.

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
    
def manuel_ezici_kontrol(komut):
    """
    Manuel ezici kontrolü (test ve bakım için)
    Args:
        komut: 'ileri', 'geri', 'dur', 'ileri_10sn', 'geri_10sn'
    """
    if not sistem.motor_kontrol_ref:
        print("⚠️ [MANUEL EZİCİ] Motor kontrol referansı yok")
        return False
    
    try:
        if komut == "ileri":
            return sistem.motor_kontrol_ref.ezici_ileri()
        elif komut == "geri":
            return sistem.motor_kontrol_ref.ezici_geri()
        elif komut == "dur":
            return sistem.motor_kontrol_ref.ezici_dur()
        elif komut == "ileri_10sn":
            return sistem.motor_kontrol_ref.ezici_ileri_10sn()
        elif komut == "geri_10sn":
            return sistem.motor_kontrol_ref.ezici_geri_10sn()
        else:
            return False
            
    except Exception as e:
        print(f"❌ [MANUEL EZİCİ] Hata: {e}")
        return False

def manuel_kirici_kontrol(komut):
    """
    Manuel kırıcı kontrolü (test ve bakım için)
    Args:
        komut: 'ileri', 'geri', 'dur', 'ileri_10sn', 'geri_10sn'
    """
    if not sistem.motor_kontrol_ref:
        print("⚠️ [MANUEL KIRICI] Motor kontrol referansı yok")
        return False
    
    try:
        if komut == "ileri":
            return sistem.motor_kontrol_ref.kirici_ileri()
        elif komut == "geri":
            return sistem.motor_kontrol_ref.kirici_geri()
        elif komut == "dur":
            return sistem.motor_kontrol_ref.kirici_dur()
            return sistem.motor_kontrol_ref.kirici_dur()
        elif komut == "ileri_10sn":
            return sistem.motor_kontrol_ref.kirici_ileri_10sn()
        elif komut == "geri_10sn":
            return sistem.motor_kontrol_ref.kirici_geri_10sn()
        else:
            return False
            
    except Exception as e:
        print(f"❌ [MANUEL KIRICI] Hata: {e}")
        return False

def yonlendirici_hareket():
    if not sistem.kabul_edilen_urunler:
        print(f"⚠️ [YÖNLENDİRME] Kabul edilen ürün kuyruğu boş.")
        sistem.iade_lojik = True
        sistem.iade_sebep = "Yönlendirme için ürün yok."
        sistem.veri_senkronizasyon_listesi.clear()  # Tüm bekleyen verileri temizle
        sistem.kabul_edilen_urunler.clear()  # Tüm kabul edilen ürünleri temizle
        return
    
    urun = sistem.kabul_edilen_urunler[0]
    sistem.son_islenen_urun = urun.copy()
    materyal_id = urun.get('materyal_turu')
    
    materyal_isimleri = {1: "PET", 2: "CAM", 3: "ALÜMİNYUM"}
    materyal_adi = materyal_isimleri.get(materyal_id, "BİLİNMEYEN")
    
    print(f"\n🔄 [YÖNLENDİRME] {materyal_adi} ürün işleniyor: {urun['barkod']}")

    if sistem.motor_ref:
        if materyal_id == 2: # Cam
            manuel_kirici_kontrol("ileri_10sn")
            sistem.motor_ref.konveyor_dur()
            sistem.motor_ref.yonlendirici_cam()
            print(f"🟦 [CAM] Cam yönlendiricisine gönderildi")
        else: # Plastik/Metal
            manuel_ezici_kontrol("ileri_10sn")  # Otomatik ezici 10 saniye ileri
            sistem.motor_ref.konveyor_dur()
            sistem.motor_ref.yonlendirici_plastik()
            print(f"🟩 [PLASTİK/METAL] Plastik/Metal yönlendiricisine gönderildi")
    
    sistem.kabul_edilen_urunler.popleft()
    print(f"📦 [KUYRUK] Kalan ürün sayısı: {len(sistem.kabul_edilen_urunler)}")
    print(f"✅ [YÖNLENDİRME] İşlem tamamlandı\n")

def lojik_yoneticisi():
    while True:
        time.sleep(0.005) # CPU kullanımını azaltmak için kısa bir uyku

        if not sistem.giris_sensor_durum and (sistem.ysi_lojik or sistem.yso_lojik):
            print("-----------------------------------------------DENEME----------------------------------------------------------------------")

        if sistem.ysi_lojik:
            sistem.ysi_lojik = False
            print("🔄 [LOJİK] YSI lojik işlemleri başlatıldı")


        if sistem.gsi_lojik:
            sistem.gsi_lojik = False
            sistem.giris_sensor_durum = True
            sistem.gsi_gecis_lojik = True
            
            if sistem.iade_lojik:
                print("🚫 [İADE AKTIF] Şişeyi Alınız.")
                log_oturum_var("İADE AKTIF - Şişeyi Alınız.")
                time.sleep(0.25)
                sistem.motor_ref.konveyor_dur()
            else:
                print("🔄 [LOJİK] GSI lojik işlemleri başlatıldı")
                log_oturum_var("LOJİK - GSI lojik işlemleri başlatıldı")
                sistem.motor_ref.konveyor_ileri()
        
        if sistem.gso_lojik:
            sistem.gso_lojik = False
            sistem.giris_sensor_durum = False

            if sistem.iade_lojik:
                
                goruntu = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
                if goruntu.mesaj=="nesne_yok":
                    print("🚫 [İADE AKTIF] Şişe alındı, nesne yok.")
                    log_oturum_var("İADE AKTIF - Şişe alındı, nesne yok.")
                    sistem.agirlik_kuyruk.clear()  # iade sırasında bekleyen ağırlıkları temizle
                    sistem.iade_lojik = False
                    sistem.barkod_lojik = False
                    
                    # Uyarı ekranını kapat - şişe geri alındı
                    sistem.veri_senkronizasyon_listesi.clear()  # iade sırasında bekleyen verileri temizle
                    sistem.kabul_edilen_urunler.clear()  # iade sırasında bekleyen kabul
                    uyari.uyari_kapat()
                    print("✅ [UYARI] Uyarı ekranı kapatıldı - şişe geri alındı")
                    log_oturum_var("UYARI - Uyarı ekranı kapatıldı - şişe geri alındı")
                else:
                    print("🚫 [İADE AKTIF] Görüntü işleme kabul etmedi iade devam.")
                    log_oturum_var("İADE AKTIF - Görüntü işleme kabul etmedi iade devam.")
                    sistem.motor_ref.konveyor_geri()
            else:
                if sistem.barkod_lojik:
                    if sistem.iade_lojik==False:
                        print("[GSO] Sistem Normal Çalışıyor. Görüntü İşleme Başlatılıyor.")
                        log_oturum_var("GSO - Sistem Normal Çalışıyor. Görüntü İşleme Başlatılıyor.")
                        
                        sistem.sensor_ref.loadcell_olc()
                        goruntu_isleme_tetikle()
                        # Normal akışta gsi_gecis_lojik'i sıfırla
                        sistem.gsi_gecis_lojik = False
                    else:
                        print("🚫 [İADE AKTIF] Görüntü İşleme Başlatılamıyor.")
                        log_oturum_var("İADE AKTIF - Görüntü İşleme Başlatılamıyor.")
                else:
                    sebep = "Barkod okunmadı"
                    print(f"🚫 [GSO] {sebep}, ürünü iade et.")
                    log_oturum_var(f"GSO - {sebep}, ürünü iade et.")
                    sistem.iade_lojik = True
                    sistem.iade_sebep = sebep

        if sistem.yso_lojik:
            sistem.yso_lojik = False
            print("🔄 [LOJİK] YSO lojik işlemleri başlatıldı")
            log_oturum_var("LOJİK - YSO lojik işlemleri başlatıldı")
            yonlendirici_hareket()

        if sistem.yonlendirici_konumda:
            sistem.yonlendirici_konumda = False
            sistem.agirlik_kuyruk.popleft() if sistem.agirlik_kuyruk else None
            # DİM-DB'ye onaylanan bildirimi gönder (ymk geldiğinde)
            if sistem.son_islenen_urun:
                dimdb_bildirim_gonder(sistem.son_islenen_urun['barkod'],sistem.son_islenen_urun['agirlik'],sistem.son_islenen_urun['materyal_turu'],sistem.son_islenen_urun['uzunluk'],sistem.son_islenen_urun['genislik'],True,0,"Ambalaj Kabul Edildi")
                sistem.son_islenen_urun = None  # Temizle
            
            if len(sistem.veri_senkronizasyon_listesi)>0 or len(sistem.kabul_edilen_urunler)>0:
                print("🔄 [LOJİK] Yönlendirici konumda, konveyör ileri")
                sistem.motor_ref.konveyor_ileri()
            else:
                if sistem.gsi_gecis_lojik and not sistem.iade_lojik:
                    print("✅ [LOJİK] Yönlendirici konumda, konveyör ileri gsi_gecis_lojik aktif")
                    sistem.motor_ref.konveyor_ileri()
                    # gsi_gecis_lojik'i burada sıfırlama! Sadece GSO'da sıfırlanmalı

                else:
                    print("✅ [LOJİK] Yönlendirici konumda, konveyör dur")
                    sistem.motor_ref.konveyor_dur()
                    # gsi_gecis_lojik sadece burada sıfırlanmalı
                    sistem.gsi_gecis_lojik = False
                    
        if sistem.agirlik is not None:
            if sistem.barkod_lojik and not sistem.iade_lojik:
                
                toplam_konveyor_agirligi = 0
                if sistem.agirlik_kuyruk:
                    for idx, agirlik in enumerate(sistem.agirlik_kuyruk):
                        toplam_konveyor_agirligi += agirlik
                        print(f"  {idx+1}. Ürün Ağırlığı: {agirlik:.2f} gr")

                toplam_olcums_agirlik = sistem.agirlik
                gercek_agirlik = toplam_olcums_agirlik - toplam_konveyor_agirligi
                
                print(f"⚖️ [AĞIRLIK] Toplam Ölçülen: {toplam_olcums_agirlik:.2f} gr")
                if toplam_konveyor_agirligi > 0:
                    print(f"⚖️ [AĞIRLIK] Konveyördeki Bilinen Ağırlık: {toplam_konveyor_agirligi:.2f} gr")
                print(f"⚖️ [AĞIRLIK] Hesaplanan Gerçek Ağırlık: {gercek_agirlik:.2f} gr")
                sistem.agirlik_kuyruk.append(gercek_agirlik)
                veri_senkronizasyonu(agirlik=gercek_agirlik)
                sistem.agirlik = None  # Sıfırla
            else:
                print(f"⚠️ [AĞIRLIK] Ölçülen ağırlık var ama barkod lojik aktif değil veya iade lojik aktif: {sistem.agirlik} gr")
                sistem.agirlik = None  # Sıfırla

        if sistem.iade_lojik:
            if len(sistem.kabul_edilen_urunler) == 0 and len(sistem.veri_senkronizasyon_listesi) == 0:
                if not sistem.iade_etildi:
                    print("🚫 [İADE] İade lojik aktif, ürün iade ediliyor...")
                    giris_iade_et(sistem.iade_sebep)  # her iade durumunda çağrılıyor
                    sistem.iade_sebep = None
                    sistem.iade_etildi = True
        else:
            # iade_lojik kapandığında tekrar aktifleşmeye izin ver
            sistem.iade_etildi = False
            
        # Konveyör durum kontrol - sistem boşken konveyörü durdur
        if len(sistem.kabul_edilen_urunler) == 0 and len(sistem.veri_senkronizasyon_listesi) == 0 and not sistem.iade_lojik:
            if not sistem.konveyor_durum_kontrol:
                print("🟢 [KONVEYÖR] Konveyör durduruluyor")
                sistem.motor_ref.konveyor_dur()
                sistem.konveyor_durum_kontrol = True
        elif sistem.konveyor_durum_kontrol:
            # Sadece durum değiştiyse flag'i sıfırla
            print("🔄 [KONVEYÖR] Konveyör durumu aktif edildi")
            sistem.konveyor_durum_kontrol = False

        if sistem.konveyor_adim_problem == True:
            sistem.konveyor_adim_problem = False
            if len(sistem.kabul_edilen_urunler) == 0 and len(sistem.veri_senkronizasyon_listesi) == 0:
                print("⚠️ [KONVEYÖR HATA] Konveyör adım problemi algılandı, sistem boş ve iade lojik değil, konveyör durduruluyor")
                if not sistem.iade_lojik:
                    sistem.motor_ref.konveyor_problem_var()
                
                else:
                    goruntu = goruntu_isleme_servisi.goruntu_yakala_ve_isle()
                    if goruntu.mesaj=="nesne_yok":
                        print("🚫 [Konveyor Motor Problem] Şişe alındı, nesne yok.")
                        sistem.iade_lojik = False
                        sistem.barkod_lojik = False
                        sistem.kabul_edilen_urunler.clear()  # iade sırasında bekleyen kabul
                        sistem.veri_senkronizasyon_listesi.clear()  # iade sırasında bekleyen
                        
                        # Uyarı ekranını kapat - şişe geri alındı
                        uyari.uyari_kapat()
                        print("✅ [UYARI] Uyarı ekranı kapatıldı - şişe geri alındı")

                    else:
                        sistem.iade_lojik = True
                        print("🚫 [Konveyor Motor Problem] Görüntü işleme kabul edildi, iade işlemi devam ediyor.")
            else:
                print("⚠️ [KONVEYÖR HATA] Konveyör adım problemi algılandı, ancak sistem boş değil veya iade lojik aktif, konveyör durdurulmadı")
                sistem.motor_ref.konveyor_problem_yok()        

def giris_iade_et(sebep):
    print(f"\n❌ [GİRİŞ İADESİ] Sebep: {sebep}")
    uyari.uyari_goster(mesaj=f"Lütfen şişeyi geri alınız : {sebep}", sure=0)
    sistem.motor_ref.konveyor_geri()

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

        sistem.iade_lojik = False
        sistem.iade_lojik_onceki_durum = False
        sistem.barkod_lojik = False
        sistem.veri_senkronizasyon_listesi.clear()
        sistem.kabul_edilen_urunler.clear()
        sistem.onaylanan_urunler.clear()

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
    if mesaj == "kmp":  
        sistem.konveyor_adim_problem = True
    if mesaj == "ykt":
        sistem.yonlendirici_kalibrasyon = True
    if mesaj == "skt":  
        sistem.seperator_kalibrasyon = True
    
def modbus_mesaj(modbus_verisi):
    veri = modbus_verisi
    #print(f"[Oturum Var Modbus] Gelen veri: {modbus_verisi}")