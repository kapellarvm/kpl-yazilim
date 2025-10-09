import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import uuid as uuid_lib

# Modern lojik yönetimi için 'transitions' kütüphanesi gereklidir.
# Kurulum: pip install transitions
from transitions import Machine

# Orijinal projenizdeki import'ların çalıştığını varsayıyoruz.
# Bu import'lar projenizin dosya yapısına göre düzenlenmelidir.
from ...veri_tabani import veritabani_yoneticisi
from ..goruntu.goruntu_isleme_servisi import GoruntuIslemeServisi
from . import uyari
from ...utils.logger import log_oturum_var, log_error, log_success, log_warning, log_system
from ...dimdb.dimdb_yoneticisi import dimdb_bildirim_gonder

# --- 1. Veri Modelleri: Durum yerine veriyi modellemek ---

@dataclass
class Urun:
    """Tek bir ürünün tüm verilerini ve durumunu tutan sınıf."""
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()))
    barkod: Optional[str] = None
    agirlik: Optional[float] = None
    materyal_turu: Optional[int] = None
    uzunluk: Optional[float] = None
    genislik: Optional[float] = None
    
    def verisi_tamam_mi(self) -> bool:
        """Ürünün işlenmesi için tüm verilerin gelip gelmediğini kontrol eder."""
        return all(v is not None for v in [self.barkod, self.agirlik, self.materyal_turu, self.uzunluk, self.genislik])

# --- 2. Veri Yönetimi: Kuyruk Lojiği ---

class IslemKuyrugu:
    """
    İşlenecek ürünlerin kuyruğunu yönetir.
    Veri senkronizasyonu ve thread güvenliği burada sağlanır.
    """
    def __init__(self, maksimum_boyut=10):
        self._kuyruk: deque[Urun] = deque()
        self._lock = threading.Lock()
        self.maksimum_boyut = maksimum_boyut

    def kuyruk_dolu_mu(self) -> bool:
        return len(self._kuyruk) >= self.maksimum_boyut

    def yeni_urun_ekle(self, barkod: str) -> Optional[Urun]:
        with self._lock:
            if self.kuyruk_dolu_mu():
                log_warning(f"Kuyruk dolu ({len(self._kuyruk)}). Yeni barkod {barkod} eklenemedi.")
                return None
            yeni_urun = Urun(barkod=barkod)
            self._kuyruk.append(yeni_urun)
            log_oturum_var(f"KUYRUK (+) - Ürün eklendi: {barkod}. Boyut: {len(self._kuyruk)}")
            return yeni_urun

    def veri_guncelle(self, **kwargs) -> Optional[Urun]:
        with self._lock:
            if not self._kuyruk:
                log_warning("Veri güncellenecek ürün kuyrukta bulunamadı.")
                return None
            
            # Kuyruktaki verisi en eksik (genellikle sonuncu) ürünü bul ve güncelle
            target_urun = self._kuyruk[-1]
            for key, value in kwargs.items():
                if hasattr(target_urun, key) and value is not None:
                    setattr(target_urun, key, value)
            
            log_oturum_var(f"KUYRUK (~) - Barkod {target_urun.barkod} güncellendi: {kwargs}")
            return target_urun
            
    def siradaki_hazir_urunu_al(self) -> Optional[Urun]:
        with self._lock:
            if self._kuyruk and self._kuyruk[0].verisi_tamam_mi():
                islenen_urun = self._kuyruk.popleft()
                log_oturum_var(f"KUYRUK (-) - Ürün işlem için alındı: {islenen_urun.barkod}. Kalan: {len(self._kuyruk)}")
                return islenen_urun
            return None

    def temizle(self):
        with self._lock:
            self._kuyruk.clear()
            log_system("İşlem kuyruğu temizlendi.")
            
    @property
    def bos_mu(self):
        return not self._kuyruk

# --- 3. Durum Yönetimi: State Machine ---

class UrunIslemeMakinesi:
    """
    Sistemin fiziksel durumunu (konveyör, yönlendirici vb.) yönetir.
    'transitions' kütüphanesi ile bir Durum Makinesi olarak tasarlanmıştır.
    """
    STATES = ['BOS', 'URUN_GELIYOR', 'ISLEM_BEKLIYOR', 'YONLENDIRME', 'IADE_EDILIYOR', 'HATA']

    def __init__(self, yonetici):
        self.yonetici = yonetici  # Ana SistemYoneticisi'ne referans
        self.son_islenen_urun: Optional[Urun] = None
        self.iade_sebebi: Optional[str] = None
        
        self.machine = Machine(model=self, states=self.STATES, initial='BOS', after_state_change="_durum_degisikligini_logla")

        # --- Geçiş Tanımları (Transitions) ---
        # Hangi olayların hangi durum geçişlerini tetikleyeceği burada tanımlanır.
        
        # 1. Normal Akış
        self.machine.add_transition('urun_geldi', 'BOS', 'URUN_GELIYOR', after='_konveyoru_baslat')
        self.machine.add_transition('urun_islem_noktasinda', 'URUN_GELIYOR', 'ISLEM_BEKLIYOR', after='_islemeyi_tetikle')
        self.machine.add_transition('dogrulama_basarili', 'ISLEM_BEKLIYOR', 'YONLENDIRME', before='_yonlendiriciyi_ayarla')
        self.machine.add_transition('yonlendirme_bitti', 'YONLENDIRME', 'BOS', after='_onay_bildirimi_gonder')

        # 2. İade Akışı
        self.machine.add_transition('iade_gerekiyor', '*', 'IADE_EDILIYOR', before='_iade_islemini_baslat')
        self.machine.add_transition('iade_tamamlandi', 'IADE_EDILIYOR', 'BOS', after='_iade_sonrasi_temizlik')

        # 3. Hata ve Reset Akışı
        self.machine.add_transition('hata_olustu', '*', 'HATA', before='_tum_sistemi_durdur')
        self.machine.add_transition('reset', '*', 'BOS', after='_sistemi_sifirla')

    # --- Callback Fonksiyonları (State'e girince/çıkınca çalışanlar) ---

    def _durum_degisikligini_logla(self):
        log_system(f"DURUM DEĞİŞİMİ: {self.machine.before_state} -> {self.state}")
        self.yonetici.aktivite_guncelle()

    def _konveyoru_baslat(self):
        log_oturum_var("Ürün giriş sensöründe. Konveyör ileri hareket başlatılıyor.")
        self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.konveyor_ileri)

    def _islemeyi_tetikle(self):
        log_oturum_var("Ürün işlem noktasında. Konveyör durduruluyor, ölçüm ve görüntü işleme başlıyor.")
        self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.konveyor_dur)
        self.yonetici.agirlik_ve_goruntu_islemeyi_baslat()

    def _yonlendiriciyi_ayarla(self, urun: Urun):
        self.son_islenen_urun = urun
        log_oturum_var(f"Doğrulama başarılı. Yönlendirici, Materyal ID {urun.materyal_turu} için ayarlanıyor.")
        
        if urun.materyal_turu == 2: # Cam
            if self.yonetici.kirici_durum: self.yonetici.manuel_kirici_kontrol("ileri_10sn")
            self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.yonlendirici_cam)
        else: # Plastik/Metal
            if self.yonetici.ezici_durum: self.yonetici.manuel_ezici_kontrol("ileri_10sn")
            self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.yonlendirici_plastik)
        
        # Klape ayarı
        if urun.materyal_turu == 1: self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.klape_plastik)
        elif urun.materyal_turu == 3: self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.klape_metal)


    def _onay_bildirimi_gonder(self):
        urun = self.son_islenen_urun
        if urun:
            log_success(f"Yönlendirme tamamlandı. Ürün kabul edildi: {urun.barkod}")
            dimdb_bildirim_gonder(urun.barkod, urun.agirlik, urun.materyal_turu, urun.uzunluk, urun.genislik, True, 0, "Ambalaj Kabul Edildi")
            self.son_islenen_urun = None
        
        # Kuyrukta hala ürün varsa konveyörü tekrar çalıştır
        if not self.yonetici.kuyruk.bos_mu:
            self.urun_geldi() # Bir sonraki ürünü işlemek için döngüyü tetikle
        else:
            log_system("Tüm ürünler işlendi, konveyör durduruldu.")
            self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.konveyor_dur)


    def _iade_islemini_baslat(self, sebep: str):
        self.iade_sebebi = sebep
        log_error(f"İADE - Sebep: {sebep}. Konveyör geri çalıştırılıyor.")
        uyari.uyari_goster(mesaj=f"Lütfen şişeyi geri alınız: {sebep}", sure=0)
        self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.konveyor_geri)

    def _iade_sonrasi_temizlik(self):
        log_oturum_var("İade tamamlandı. Sistem normale dönüyor.")
        uyari.uyari_kapat()
        self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.konveyor_dur)
        self.iade_sebebi = None

    def _tum_sistemi_durdur(self, hata_mesaji: str):
        log_error(f"KRİTİK HATA: {hata_mesaji}. Tüm motorlar durduruluyor.")
        # Burada tüm motorları ve işlemleri durduracak acil durum kodları olmalı
        self.yonetici.guvenli_motor_komut(self.yonetici.motor_ref.konveyor_dur)
        # ... diğer motorlar için durdurma komutları

    def _sistemi_sifirla(self):
        log_system("Sistem sıfırlanıyor, başlangıç durumuna dönülüyor.")
        self.yonetici.kuyruk.temizle()
        self.son_islenen_urun = None
        self.iade_sebebi = None


# --- 4. Orkestrasyon: Ana Yönetici Sınıfı ---

class SistemYoneticisi:
    """
    Tüm sistemi yöneten, referansları tutan ve olayları yönlendiren ana sınıf.
    Singleton deseni ile tek bir nesne olmasını sağlar.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SistemYoneticisi, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Referanslar
        self.motor_ref = None
        self.sensor_ref = None
        self.motor_kontrol_ref = None
        
        # Bileşenler
        self.goruntu_isleme_servisi = GoruntuIslemeServisi()
        self.kuyruk = IslemKuyrugu()
        self.makine = UrunIslemeMakinesi(self) # State Machine
        
        # Durum ve Kontrol
        self.lojik_thread = None
        self.lojik_thread_calisiyor = threading.Event()
        
        # Güvenlik ve Timeout
        self.son_aktivite_zamani = time.time()
        self.timeout_suresi = 30.0
        
        # Diğer durumlar
        self.ezici_durum = False
        self.kirici_durum = False


    def baslat(self):
        if self.lojik_thread and self.lojik_thread.is_alive():
            log_warning("Lojik yöneticisi zaten çalışıyor.")
            return

        self.lojik_thread_calisiyor.set()
        self.lojik_thread = threading.Thread(target=self._lojik_dongusu, daemon=True)
        self.lojik_thread.start()
        log_system("Sistem Yöneticisi ve Lojik Döngüsü Başlatıldı.")
        
        # Başlangıç temizliği
        self.makine.reset()
        self.guvenli_motor_komut(self.motor_ref.motorlari_aktif_et)
        self.guvenli_motor_komut(self.motor_ref.konveyor_dur)
        self.guvenli_sensor_komut(self.sensor_ref.tare)
        self.guvenli_sensor_komut(self.sensor_ref.led_ac)


    def durdur(self):
        self.lojik_thread_calisiyor.clear()
        if self.lojik_thread and self.lojik_thread.is_alive():
            self.lojik_thread.join(timeout=2)
        log_system("Sistem Yöneticisi Durduruldu.")

    def _lojik_dongusu(self):
        """
        Arka planda çalışan, kuyruktaki hazır ürünleri kontrol eden ve
        timeout gibi periyodik kontrolleri yapan döngü.
        """
        while self.lojik_thread_calisiyor.is_set():
            try:
                # 1. İşlenmeye hazır ürün var mı diye kontrol et
                hazir_urun = self.kuyruk.siradaki_hazir_urunu_al()
                if hazir_urun:
                    self._urunu_dogrula_ve_yonlendir(hazir_urun)

                # 2. Timeout kontrolü
                if time.time() - self.son_aktivite_zamani > self.timeout_suresi:
                    log_warning(f"Sistem timeout! Son aktivite {self.timeout_suresi} saniye önce.")
                    self.makine.iade_gerekiyor("Sistem zaman aşımına uğradı.")
                
                # ... diğer periyodik kontroller ...

            except Exception as e:
                log_error(f"Lojik döngüsü hatası: {e}")
                self.makine.hata_olustu(f"Lojik döngüsü hatası: {e}")

            time.sleep(0.1) # CPU kullanımını düşür

    def _urunu_dogrula_ve_yonlendir(self, urun: Urun):
        kabul_edildi, sebep_kodu, sebep_mesaji = self._dogrulama(urun)
        
        if kabul_edildi:
            self.makine.dogrulama_basarili(urun=urun)
        else:
            dimdb_bildirim_gonder(urun.barkod, urun.agirlik, urun.materyal_turu, urun.uzunluk, urun.genislik, False, sebep_kodu, sebep_mesaji)
            self.makine.iade_gerekiyor(sebep_mesaji)

    def _dogrulama(self, urun: Urun) -> (bool, int, str):
        # Bu fonksiyon orijinal 'dogrulama' fonksiyonunuzun mantığını içerir.
        # Daha temiz olması için buraya alındı.
        db_urun = veritabani_yoneticisi.barkodu_dogrula(urun.barkod)
        if not db_urun:
            return False, 1, f"Ürün veritabanında yok (Barkod: {urun.barkod})"
        
        # Ağırlık, boyut ve materyal kontrolleri... (Orijinal koddaki mantık aynen uygulanır)
        # Örnek Ağırlık Kontrolü:
        min_agirlik = db_urun.get('packMinWeight', urun.agirlik)
        max_agirlik = db_urun.get('packMaxWeight', urun.agirlik)
        if not (min_agirlik - 20 <= urun.agirlik <= max_agirlik + 20):
            return False, 2, f"Ağırlık sınırları dışında ({urun.agirlik}g)"
        
        # ... diğer kontroller ...
        
        return True, 0, "Ambalaj Kabul Edildi"


    def aktivite_guncelle(self):
        self.son_aktivite_zamani = time.time()

    def agirlik_ve_goruntu_islemeyi_baslat(self):
        # Ağırlık ve görüntü işleme eş zamanlı çalışabilir.
        threading.Thread(target=self._agirlik_olc_ve_guncelle).start()
        threading.Thread(target=self._goruntu_isle_ve_guncelle).start()

    def _agirlik_olc_ve_guncelle(self):
        try:
            # Gerçek ağırlık hesaplama mantığı (kuyruktaki diğer ağırlıkları çıkarma)
            # Bu kısım basitleştirildi, gerekirse orijinal mantık eklenebilir.
            self.guvenli_sensor_komut(self.sensor_ref.loadcell_olc)
            # loadcell_olc sonucu bir şekilde 'agirlik' değişkenine gelmeli.
            # Şimdilik direkt mesajla geldiğini varsayıyoruz.
        except Exception as e:
            log_error(f"Ağırlık ölçüm hatası: {e}")
            self.makine.iade_gerekiyor("Ağırlık sensörü okunamadı.")
            
    def _goruntu_isle_ve_guncelle(self):
        try:
            sonuc = self.goruntu_isleme_servisi.goruntu_yakala_ve_isle()
            if not sonuc or not hasattr(sonuc, 'tur'):
                raise ValueError("Geçersiz görüntü işleme sonucu")
            
            self.kuyruk.veri_guncelle(
                materyal_turu=sonuc.tur.value,
                uzunluk=float(sonuc.genislik_mm),
                genislik=float(sonuc.yukseklik_mm)
            )
        except Exception as e:
            log_error(f"Görüntü işleme hatası: {e}")
            self.makine.iade_gerekiyor(f"Görüntü işleme hatası: {e}")


    # --- DIŞ DÜNYA İLE İLETİŞİM ---

    def mesaj_isle(self, mesaj: str):
        mesaj = mesaj.strip().lower()
        
        if mesaj == "oturum_var":
            self.baslat()
            return
            
        if self.makine.state == 'HATA':
            log_warning(f"Sistem HATA durumunda. Sadece 'reset' komutu kabul edilir. Gelen mesaj: {mesaj}")
            if mesaj == "reset": self.makine.reset()
            return

        # Sensör Olayları -> State Machine Tetikleyicileri
        if mesaj == "gsi": self.makine.urun_geldi()
        elif mesaj == "gso":
            if self.makine.state == 'IADE_EDILIYOR':
                 self.makine.iade_tamamlandi()
            elif self.makine.state == 'URUN_GELIYOR':
                 self.makine.urun_islem_noktasinda()
        elif mesaj == "ymk":
            if self.makine.state == 'YONLENDIRME':
                self.makine.yonlendirme_bitti()
        
        # Veri Girişleri -> Kuyruk Güncellemeleri
        elif mesaj.startswith("a:"):
            try:
                agirlik = float(mesaj.split(":")[1].replace(",", "."))
                self.kuyruk.veri_guncelle(agirlik=agirlik)
            except (ValueError, IndexError) as e:
                log_error(f"Ağırlık verisi parse hatası: {e}")

        # Hata Mesajları -> Hata Durumuna Geçiş
        elif mesaj in ["kmh", "ymh", "smh", "kmp"]:
            self.makine.hata_olustu(f"Motor hatası alındı: {mesaj}")

    def barkod_verisi_al(self, barkod: str):
        if self.makine.state in ['IADE_EDILIYOR', 'HATA']:
            log_warning(f"Sistem {self.makine.state} durumunda, yeni barkod ({barkod}) kabul edilmiyor.")
            return

        if self.kuyruk.kuyruk_dolu_mu():
            self.makine.iade_gerekiyor("Sistem kapasitesi dolu, yeni ürün kabul edilemiyor.")
            return
            
        self.kuyruk.yeni_urun_ekle(barkod)
        self.aktivite_guncelle()

    # --- Yardımcı ve Güvenlik Fonksiyonları ---
    # Orijinal koddaki guvenli_motor_komut vb. fonksiyonlar buraya eklenebilir.
    def guvenli_motor_komut(self, komut_func, *args, **kwargs):
        if not self.motor_ref: return False
        try:
            return komut_func(*args, **kwargs)
        except Exception as e:
            self.makine.hata_olustu(f"Motor komutu hatası: {e}")
            return False

    def guvenli_sensor_komut(self, komut_func, *args, **kwargs):
        if not self.sensor_ref: return False
        try:
            return komut_func(*args, **kwargs)
        except Exception as e:
            self.makine.hata_olustu(f"Sensör komutu hatası: {e}")
            return False
            
    # Manuel kontrol fonksiyonları (orijinaldeki gibi)
    def manuel_ezici_kontrol(self, komut):
        # ...
        pass
        
    def manuel_kirici_kontrol(self, komut):
        # ...
        pass

# --- SİSTEMİN BAŞLATILMASI VE KULLANIMI ---

# Tekil (singleton) sistem yöneticisi nesnesi oluşturulur.
sistem_yoneticisi = SistemYoneticisi()

def motor_referansini_ayarla(motor):
    sistem_yoneticisi.motor_ref = motor
    log_system("Motor referansı ayarlandı.")

def sensor_referansini_ayarla(sensor):
    sistem_yoneticisi.sensor_ref = sensor
    log_system("Sensör referansı ayarlandı.")

def motor_kontrol_referansini_ayarla(motor_kontrol):
    sistem_yoneticisi.motor_kontrol_ref = motor_kontrol
    log_system("Motor kontrol (GA500) referansı ayarlandı.")

# Dış dünyadan gelen olaylar artık bu merkezi fonksiyonlara yönlendirilir.
def mesaj_isle(mesaj):
    sistem_yoneticisi.mesaj_isle(mesaj)

def barkod_verisi_al(barcode):
    sistem_yoneticisi.barkod_verisi_al(barcode)
