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
from rvm_sistemi.makine.seri.system_state_manager import system_state, SystemState, CardState
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
                
                # System state kontrolü - reconnection sırasında ping atma
                from .system_state_manager import system_state
                if system_state.is_system_busy():
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
        
        # EK: Motor kartı yazma hatası kontrolü
        if hasattr(self, 'motor_karti') and self.motor_karti:
            # Motor kartı yazma hatası varsa ve sistem meşgul değilse reset yap
            if (hasattr(self.motor_karti, 'port_adi') and 
                self.motor_karti.port_adi and 
                not self.motor_karti.saglikli and
                not system_state.is_system_busy()):
                
                print(f"🔧 [PORT-SAĞLIK] Motor kartı yazma hatası tespit edildi - reset yapılıyor")
                log_system("Motor kartı yazma hatası tespit edildi - reset yapılıyor")
                self._kartlari_resetle(["motor"])
        
        # EK: Motor kartı için özel kontrol - port bulunmuş ama bağlantı kurulamıyorsa
        if hasattr(self, 'motor_karti') and self.motor_karti:
            # Motor kartı port bulunmuş ama bağlantı kurulamıyorsa
            if (hasattr(self.motor_karti, 'port_adi') and 
                self.motor_karti.port_adi and 
                not self.motor_karti.saglikli):
                
                # Status test ile motor kartının gerçekten çalışıp çalışmadığını kontrol et
                print(f"🔧 [PORT-SAĞLIK] Motor kartı port bulunmuş ama bağlantı kurulamıyor - status test yapılıyor")
                log_system("Motor kartı port bulunmuş ama bağlantı kurulamıyor - status test yapılıyor")
                
                if hasattr(self.motor_karti, 'status_test'):
                    status_ok = self.motor_karti.status_test()
                    if status_ok:
                        print(f"✅ [PORT-SAĞLIK] Motor kartı status test başarılı - yeniden başlatma gerekmiyor")
                        log_system("Motor kartı status test başarılı - yeniden başlatma gerekmiyor")
                        return
                    else:
                        print(f"❌ [PORT-SAĞLIK] Motor kartı status test başarısız - yeniden başlatılıyor")
                        log_system("Motor kartı status test başarısız - yeniden başlatılıyor")
                        self._kartlari_yeniden_baslat({"motor": self.motor_karti.port_adi})
                else:
                    print(f"⚠️  [PORT-SAĞLIK] Motor kartı status test fonksiyonu yok - yeniden başlatılıyor")
                    log_system("Motor kartı status test fonksiyonu yok - yeniden başlatılıyor")
                    self._kartlari_yeniden_baslat({"motor": self.motor_karti.port_adi})
    
    def _kartlari_resetle(self, kritik_kartlar: list):
        """
        Kartları resetle - System State Manager ile
        
        Args:
            kritik_kartlar: Resetlenecek kart listesi
        """
        # System state manager ile reset kontrolü
        if not system_state.can_start_reset():
            # Eğer sistem RECONNECTING durumundaysa ve uzun süredir devam ediyorsa force reset yap
            current_state = system_state.get_system_state()
            if current_state.value == "reconnecting":
                # RECONNECTING durumunda 30 saniyeden fazla devam ediyorsa force reset
                if system_state.is_reconnection_timeout():
                    print(f"⚠️  [PORT-SAĞLIK] RECONNECTING timeout - Force reset yapılıyor!")
                    log_warning("RECONNECTING timeout - Force reset yapılıyor")
                else:
                    print(f"❌ [PORT-SAĞLIK] Reset zaten devam ediyor veya çok erken!")
                    log_warning("Reset zaten devam ediyor veya minimum süre geçmedi")
                    return
            else:
                print(f"❌ [PORT-SAĞLIK] Reset zaten devam ediyor veya çok erken!")
                log_warning("Reset zaten devam ediyor veya minimum süre geçmedi")
                return
        
        # Reset operasyonu başlat
        operation_id = system_state.start_reset_operation(
            cards=set(kritik_kartlar), 
            initiated_by="port_health_service"
        )
        
        if not operation_id:
            print(f"❌ [PORT-SAĞLIK] Reset operasyonu başlatılamadı!")
            log_error("Reset operasyonu başlatılamadı")
            return
        
        print(f"\n{'='*60}")
        print(f"🔄 [PORT-SAĞLIK] KRİTİK KARTLAR RESETLENİYOR: {kritik_kartlar}")
        print(f"🆔 Reset ID: {operation_id}")
        print(f"{'='*60}\n")
        log_warning(f"Kartlar resetleniyor: {kritik_kartlar} (ID: {operation_id})")
        
        try:
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
            import os
            import subprocess
            script_path = os.path.join(os.path.dirname(__file__), "usb_reset_all.sh")
            
            if os.path.exists(script_path):
                print(f"🔧 [PORT-SAĞLIK] Agresif USB reset başlatılıyor...")
                log_system("Agresif USB reset başlatılıyor...")
                result = subprocess.run(['sudo', script_path], 
                                     capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"✅ [PORT-SAĞLIK] USB reset başarılı!")
                    log_success("USB reset başarılı")
                    reset_success = True
                else:
                    print(f"❌ [PORT-SAĞLIK] USB reset hatası: {result.stderr}")
                    log_error(f"USB reset hatası: {result.stderr}")
                    reset_success = False
            else:
                print(f"❌ [PORT-SAĞLIK] USB reset script bulunamadı: {script_path}")
                log_error(f"USB reset script bulunamadı: {script_path}")
                reset_success = False
            
            # Reset operasyonunu bitir
            system_state.finish_reset_operation(operation_id, reset_success)
            
            if reset_success:
                # Sistem durumu RECONNECTING oldu, şimdi portları yeniden bağla
                print(f"⏳ [PORT-SAĞLIK] USB reset sonrası stabilizasyon bekleniyor...")
                time.sleep(8)  # Embedded sistemlerin tamamen hazır olması için
                
                # Portları yeniden bağla
                print(f"🔍 [PORT-SAĞLIK] Portlar yeniden aranıyor...")
                basarili, mesaj, portlar = self.port_yonetici.baglan(
                    try_usb_reset=False,  # Zaten reset yaptık
                    max_retries=2,  # Daha fazla deneme
                    kritik_kartlar=["motor", "sensor"]
                )
                
                if basarili:
                    print(f"✅ [PORT-SAĞLIK] Portlar başarıyla yeniden bağlandı: {portlar}")
                    log_success(f"Portlar yeniden bağlandı: {portlar}")
                    self._durumlari_sifirla()
                    
                    # Kartları yeniden başlat
                    self._kartlari_yeniden_baslat(portlar)
                    
                    # Sistem durumunu NORMAL'e döndür
                    system_state.set_system_state(SystemState.NORMAL, "Port sağlık servisi reset tamamlandı")
                else:
                    print(f"❌ [PORT-SAĞLIK] Port yeniden bağlantı hatası: {mesaj}")
                    log_error(f"Port yeniden bağlantı hatası: {mesaj}")
                    
                    # Kartları error durumuna al
                    for card in kritik_kartlar:
                        system_state.set_card_state(card, CardState.ERROR, "Reset sonrası port bulunamadı")
            
        except Exception as e:
            print(f"❌ [PORT-SAĞLIK] Reset işlemi hatası: {e}")
            log_error(f"Reset işlemi hatası: {e}")
            
            # Reset operasyonunu başarısız olarak bitir
            system_state.finish_reset_operation(operation_id, False)
        
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
            
            # ÖNEMLİ: Kartların otomatik port arama yapmasını engelle
            # Çünkü bu fonksiyon çağrıldığında portlar ZATENbulunmuş durumda
            
            # Motor kartı
            if "motor" in portlar:
                print(f"  🔧 Motor kartı: {portlar['motor']}")
                self.motor_karti.dinlemeyi_durdur()  # Önce mevcut thread'leri durdur
                time.sleep(0.5)  # Thread'lerin tamamen durması için bekle
                self.motor_karti.port_adi = portlar["motor"]
                self.motor_karti._first_connection = True  # İlk bağlantı flag'ini resetle
                self.motor_karti._is_reconnecting = False  # Reconnect flag'ini sıfırla
                
                # ÖNCE PORTU AÇ
                if self.motor_karti.portu_ac():
                    print(f"  ✓ Motor port açıldı: {portlar['motor']}")
                    # Sonra thread'leri başlat
                    self.motor_karti.dinlemeyi_baslat()
                    
                    # Thread'lerin başlamasını bekle
                    time.sleep(1)  # Thread'lerin başlaması için bekle
                    
                    # Thread'lerin düzgün başladığından emin ol
                    if not self.motor_karti._is_port_ready():
                        print(f"  ⚠️  Motor thread'leri düzgün başlamamış, yeniden başlatılıyor")
                        # Thread durumunu kontrol et
                        self.motor_karti.thread_durumu_kontrol()
                        self.motor_karti.dinlemeyi_durdur()
                        time.sleep(0.5)
                        self.motor_karti.dinlemeyi_baslat()
                        time.sleep(1)  # Tekrar bekle
                        # Tekrar kontrol et
                        self.motor_karti.thread_durumu_kontrol()
                    
                    # Reset komutu _try_connect_to_port'ta gönderiliyor
                    
                    # Sonra parametreleri gönder
                    time.sleep(0.5)
                    self.motor_karti.parametre_gonder()
                    
                    # Thread'lerin düzgün başladığından emin ol
                    time.sleep(0.5)
                    if not self.motor_karti._is_port_ready():
                        print(f"  ⚠️  Motor thread'leri düzgün başlamamış, yeniden başlatılıyor")
                        self.motor_karti.dinlemeyi_durdur()
                        time.sleep(0.5)
                        self.motor_karti.dinlemeyi_baslat()
                        time.sleep(0.5)
                    
                    print(f"  ✅ Motor kartı başlatıldı ve resetlendi")
                else:
                    print(f"  ❌ Motor portu açılamadı!")
            
            # Sensor kartı
            if "sensor" in portlar:
                print(f"  🔧 Sensor kartı: {portlar['sensor']}")
                self.sensor_karti.dinlemeyi_durdur()  # Önce mevcut thread'leri durdur
                time.sleep(0.5)  # Thread'lerin tamamen durması için bekle
                self.sensor_karti.port_adi = portlar["sensor"]
                self.sensor_karti._first_connection = True  # İlk bağlantı flag'ini resetle
                self.sensor_karti._is_reconnecting = False  # Reconnect flag'ini sıfırla
                
                # ÖNCE PORTU AÇ
                if self.sensor_karti.portu_ac():
                    print(f"  ✓ Sensor port açıldı: {portlar['sensor']}")
                    # Sonra thread'leri başlat
                    self.sensor_karti.dinlemeyi_baslat()
                    print(f"  ✅ Sensor kartı başlatıldı")
                else:
                    print(f"  ❌ Sensor portu açılamadı!")
            
            # Embedded sistemler USB reset script'inde zaten 5 saniye boot bekledi
            # Sadece kısa bir stabilizasyon beklemesi yeterli
            print(f"⏳ [PORT-SAĞLIK] Kartların stabilizasyonu için 2 saniye bekleniyor...")
            time.sleep(2)
            print(f"✅ [PORT-SAĞLIK] Kartlar hazır - ping/pong testi başlayacak!")
                    
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
