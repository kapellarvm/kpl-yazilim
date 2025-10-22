"""
Port Sağlık Servisi
Motor ve sensör kartlarının sağlık durumunu izler ve gerektiğinde müdahale eder.
"""

import threading
import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import (
    log_system, log_error, log_success, log_warning
)


class SaglikDurumu(Enum):
    """Kart sağlık durumu"""
    SAGLIKLI = "saglikli"
    UYARI = "uyari"
    KRITIK = "kritik"
    BAGLANTI_YOK = "baglanti_yok"


@dataclass
class KartDurumu:
    """Kart durum bilgisi"""
    son_pong_zamani: float = 0
    basarisiz_ping: int = 0
    durum: SaglikDurumu = SaglikDurumu.BAGLANTI_YOK
    reset_deneme: int = 0


class PortSaglikServisi:
    """
    Port sağlık servisi - Motor ve sensör kartlarının sağlığını izler
    """
    
    # Konfigürasyon sabitleri
    PING_ARASI_SURE = 5  # Ping kontrolleri arası süre (saniye)
    MAX_PING_HATA = 5    # Maksimum başarısız ping sayısı
    RESET_BEKLEME = 10   # Reset sonrası bekleme süresi
    MAX_RESET_DENEME = 3 # Maksimum reset deneme sayısı
    
    def __init__(self, motor_karti, sensor_karti):
        """
        Port sağlık servisi başlatıcı
        
        Args:
            motor_karti: Motor kartı nesnesi
            sensor_karti: Sensör kartı nesnesi
        """
        self.motor_karti = motor_karti
        self.sensor_karti = sensor_karti
        self.port_yonetici = KartHaberlesmeServis()
        
        # Durum takibi
        self.kart_durumlari: Dict[str, KartDurumu] = {
            "motor": KartDurumu(),
            "sensor": KartDurumu()
        }
        
        # Thread yönetimi
        self.running = False
        self.oturum_var = False
        self._monitor_thread = None
        self._thread_lock = threading.Lock()
        
        # İlk durumları ayarla
        self._durumlari_sifirla()
        
        log_system("Port Sağlık Servisi başlatıldı")
    
    def servisi_baslat(self):
        """Sağlık izleme servisini başlat"""
        with self._thread_lock:
            if self.running:
                return
            
            self.running = True
            self._monitor_thread = threading.Thread(
                target=self._izleme_worker,
                daemon=True,
                name="port_saglik_monitor"
            )
            self._monitor_thread.start()
            log_success("Port sağlık izleme başlatıldı")
    
    def servisi_durdur(self):
        """Sağlık izleme servisini durdur"""
        with self._thread_lock:
            if not self.running:
                return
            
            self.running = False
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=2)
            
            log_warning("Port sağlık izleme durduruldu")
    
    def oturum_durumu_guncelle(self, oturum_var: bool):
        """
        Oturum durumunu güncelle
        
        Args:
            oturum_var: Oturum aktif mi?
        """
        self.oturum_var = oturum_var
        if oturum_var:
            self.servisi_durdur()
            log_system("Oturum aktif - Port sağlık servisi duraklatıldı")
        else:
            self.servisi_baslat()
            log_system("Oturum pasif - Port sağlık servisi devam ediyor")
    
    def _izleme_worker(self):
        """Sürekli izleme thread'i"""
        while self.running:
            try:
                # Oturum varsa atla
                if self.oturum_var:
                    time.sleep(1)
                    continue
                
                # Kartları kontrol et
                self._kartlari_kontrol_et()
                
                # Bekleme
                time.sleep(self.PING_ARASI_SURE)
                
            except Exception as e:
                log_error(f"Port sağlık izleme hatası: {e}")
                time.sleep(1)
    
    def _kartlari_kontrol_et(self):
        """Tüm kartların sağlık kontrolü"""
        # Motor kartı kontrolü
        self._kart_ping_kontrol(
            kart=self.motor_karti,
            kart_adi="motor"
        )
        
        # Sensör kartı kontrolü
        self._kart_ping_kontrol(
            kart=self.sensor_karti,
            kart_adi="sensor"
        )
        
        # Durumları değerlendir
        self._durumlari_degerlendir()
    
    def _kart_ping_kontrol(self, kart, kart_adi: str):
        """
        Kart ping kontrolü
        
        Args:
            kart: Kontrol edilecek kart nesnesi
            kart_adi: Kart adı (motor/sensor)
        """
        durum = self.kart_durumlari[kart_adi]
        
        # Ping gönder (sessiz)
        if kart.ping():
            # Başarılı ping
            if kart.saglikli:
                # Sadece log'da kaydet, print yapma
                durum.son_pong_zamani = time.time()
                durum.basarisiz_ping = 0
                durum.durum = SaglikDurumu.SAGLIKLI
                return
        
        # Başarısız ping - sadece bu durumda print yap
        durum.basarisiz_ping += 1
        gecen_sure = time.time() - durum.son_pong_zamani
        
        print(f"❌ [PORT-SAĞLIK] {kart_adi.upper()} → PONG alınamadı! (Başarısız: {durum.basarisiz_ping}/{self.MAX_PING_HATA})")
        
        # Durum güncelle
        if durum.basarisiz_ping >= self.MAX_PING_HATA:
            durum.durum = SaglikDurumu.KRITIK
            print(f"🚨 [PORT-SAĞLIK] {kart_adi.upper()} → KRİTİK DURUM! USB reset gerekiyor...")
        elif gecen_sure > self.PING_ARASI_SURE * 2:
            durum.durum = SaglikDurumu.UYARI
            print(f"⚠️  [PORT-SAĞLIK] {kart_adi.upper()} → UYARI! Son pong: {gecen_sure:.1f}s önce")
    
    def _durumlari_degerlendir(self):
        """Kart durumlarını değerlendir ve gerekirse müdahale et"""
        kritik_kartlar = []
        
        # Kritik durumları tespit et
        for kart_adi, durum in self.kart_durumlari.items():
            if durum.durum == SaglikDurumu.KRITIK:
                kritik_kartlar.append(kart_adi)
                log_error(f"{kart_adi.upper()} kartı kritik durumda!")
        
        # Kritik durum varsa müdahale et
        if kritik_kartlar:
            self._kartlari_resetle(kritik_kartlar)
    
    def _kartlari_resetle(self, kritik_kartlar: list):
        """
        Kartları resetle
        
        Args:
            kritik_kartlar: Resetlenecek kart listesi
        """
        print(f"\n{'='*60}")
        print(f"🔄 [PORT-SAĞLIK] KRİTİK KARTLAR RESETLENİYOR: {kritik_kartlar}")
        print(f"{'='*60}\n")
        log_warning(f"Kartlar resetleniyor: {kritik_kartlar}")
        
        # Önce tüm portları kapat
        print("🔌 [PORT-SAĞLIK] Tüm portlar kapatılıyor...")
        self._tum_portlari_kapat()
        
        # Reset sayacını kontrol et
        for kart_adi in kritik_kartlar:
            durum = self.kart_durumlari[kart_adi]
            durum.reset_deneme += 1
            
            if durum.reset_deneme > self.MAX_RESET_DENEME:
                print(f"❌ [PORT-SAĞLIK] {kart_adi.upper()} maksimum reset sayısına ulaştı!")
                log_error(f"{kart_adi.upper()} kartı maksimum reset sayısına ulaştı!")
                continue
        
        # Agresif USB reset uygula (TÜM USB portları)
        try:
            import os
            import subprocess
            script_path = os.path.join(os.path.dirname(__file__), "usb_reset_all.sh")
            
            if os.path.exists(script_path):
                print(f"🔧 [PORT-SAĞLIK] Agresif USB reset başlatılıyor...")
                log_system("Agresif USB reset başlatılıyor...")
                result = subprocess.run(['sudo', script_path], 
                                     capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"✅ [PORT-SAĞLIK] USB reset başarılı!")
                    log_success("USB reset başarılı")
                else:
                    print(f"❌ [PORT-SAĞLIK] USB reset hatası: {result.stderr}")
                    log_error(f"USB reset hatası: {result.stderr}")
            else:
                print(f"❌ [PORT-SAĞLIK] USB reset script bulunamadı: {script_path}")
                log_error(f"USB reset script bulunamadı: {script_path}")
                
        except Exception as e:
            print(f"❌ [PORT-SAĞLIK] USB reset hatası: {e}")
            log_error(f"USB reset hatası: {e}")
        
        # Bekleme süresi
        print(f"⏳ [PORT-SAĞLIK] {self.RESET_BEKLEME} saniye bekleniyor...")
        time.sleep(self.RESET_BEKLEME)
        
        # Portları yeniden bağla
        print(f"🔍 [PORT-SAĞLIK] Portlar yeniden aranıyor...")
        basarili, mesaj, portlar = self.port_yonetici.baglan(
            try_usb_reset=False,  # Zaten reset yaptık
            max_retries=1,
            kritik_kartlar=["motor", "sensor"]
        )
        
        if basarili:
            print(f"✅ [PORT-SAĞLIK] Portlar başarıyla yeniden bağlandı: {portlar}")
            log_success(f"Portlar yeniden bağlandı: {portlar}")
            self._durumlari_sifirla()
            
            # Kartları yeniden başlat
            self._kartlari_yeniden_baslat(portlar)
        else:
            print(f"❌ [PORT-SAĞLIK] Port yeniden bağlantı hatası: {mesaj}")
            log_error(f"Port yeniden bağlantı hatası: {mesaj}")
        
        print(f"\n{'='*60}\n")
    
    def _tum_portlari_kapat(self):
        """Tüm portları güvenli şekilde kapat"""
        try:
            # Motor kartı portunu kapat
            if self.motor_karti.seri_nesnesi:
                self.motor_karti.dinlemeyi_durdur()
                if self.motor_karti.seri_nesnesi.is_open:
                    self.motor_karti.seri_nesnesi.close()
            
            # Sensör kartı portunu kapat
            if self.sensor_karti.seri_nesnesi:
                self.sensor_karti.dinlemeyi_durdur()
                if self.sensor_karti.seri_nesnesi.is_open:
                    self.sensor_karti.seri_nesnesi.close()
            
            # Port yöneticisi üzerinden tüm portları kapat
            self.port_yonetici._close_all_ports()
            
            log_success("Tüm portlar kapatıldı")
            
        except Exception as e:
            log_error(f"Port kapatma hatası: {e}")
    
    def _kartlari_yeniden_baslat(self, portlar: dict):
        """
        Kartları yeniden başlat
        
        Args:
            portlar: Port bilgileri (örn: {"motor": "/dev/ttyUSB0", "sensor": "/dev/ttyUSB1"})
        """
        try:
            print("🔄 [PORT-SAĞLIK] Kartlar yeniden başlatılıyor...")
            
            # Motor kartı
            if "motor" in portlar:
                print(f"  🔧 Motor kartı: {portlar['motor']}")
                self.motor_karti.dinlemeyi_durdur()  # Önce mevcut thread'leri durdur
                time.sleep(0.5)  # Thread'lerin tamamen durması için bekle
                self.motor_karti.port_adi = portlar["motor"]
                self.motor_karti._first_connection = True  # İlk bağlantı flag'ini resetle
                
                # ÖNCE PORTU AÇ
                if self.motor_karti.portu_ac():
                    print(f"  ✓ Motor port açıldı: {portlar['motor']}")
                    # Sonra thread'leri başlat
                    self.motor_karti.dinlemeyi_baslat()
                    # Motor parametrelerini gönder
                    time.sleep(0.5)
                    self.motor_karti.parametre_gonder()
                    print(f"  ✅ Motor kartı başlatıldı")
                else:
                    print(f"  ❌ Motor portu açılamadı!")
            
            # Sensor kartı
            if "sensor" in portlar:
                print(f"  🔧 Sensor kartı: {portlar['sensor']}")
                self.sensor_karti.dinlemeyi_durdur()  # Önce mevcut thread'leri durdur
                time.sleep(0.5)  # Thread'lerin tamamen durması için bekle
                self.sensor_karti.port_adi = portlar["sensor"]
                self.sensor_karti._first_connection = True  # İlk bağlantı flag'ini resetle
                
                # ÖNCE PORTU AÇ
                if self.sensor_karti.portu_ac():
                    print(f"  ✓ Sensor port açıldı: {portlar['sensor']}")
                    # Sonra thread'leri başlat
                    self.sensor_karti.dinlemeyi_baslat()
                    print(f"  ✅ Sensor kartı başlatıldı")
                else:
                    print(f"  ❌ Sensor portu açılamadı!")
            
            # Kartların tamamen hazır olması için bekle
            print(f"⏳ [PORT-SAĞLIK] Kartların hazır olması için 5 saniye bekleniyor...")
            time.sleep(5)  # Daha uzun bekleme - kartların resetlendi mesajı göndermesi için
            print(f"✅ [PORT-SAĞLIK] Kartlar hazır - ping/pong testi başlayabilir!")
                    
        except Exception as e:
            print(f"❌ [PORT-SAĞLIK] Kart yeniden başlatma hatası: {e}")
            log_error(f"Kart yeniden başlatma hatası: {e}")
    
    def _durumlari_sifirla(self):
        """Kart durumlarını sıfırla"""
        for durum in self.kart_durumlari.values():
            durum.son_pong_zamani = time.time()
            durum.basarisiz_ping = 0
            durum.durum = SaglikDurumu.SAGLIKLI
            durum.reset_deneme = 0
