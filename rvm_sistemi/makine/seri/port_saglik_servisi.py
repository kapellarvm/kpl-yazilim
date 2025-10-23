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
    son_reconnection_zamani: float = 0  # Son başarılı reconnection zamanı


class PortSaglikServisi:
    """
    Port sağlık servisi - Motor ve sensör kartlarının sağlığını izler
    """
    
    # Konfigürasyon sabitleri - daha sık kontrol
    PING_ARASI_SURE = 3  # Ping kontrolleri arası süre (saniye) - daha sık
    MAX_PING_HATA = 5    # Maksimum başarısız ping sayısı - 5 ping başarısızlığında müdahale
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

        # Durum değişikliği takibi (görsel mesaj için)
        self._last_health_status = None  # "healthy", "warning", "critical"

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

                # ✅ Global busy check kaldırıldı - her kartın kendi reconnection kontrolü var
                # Kartları kontrol et (her kart kendi reconnection durumunu kontrol eder)
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
        Kart ping kontrolü - RECONNECTION BYPASS - SESLİ VERSİYON
        
        Args:
            kart: Kontrol edilecek kart nesnesi
            kart_adi: Kart adı (motor/sensor)
        """
        durum = self.kart_durumlari[kart_adi]
        
        # ✅ RECONNECTION DEVAM EDİYORSA PING ATMA (minimum 30s bekle)
        if system_state.is_card_reconnecting(kart_adi):
            reconnect_duration = system_state.get_reconnection_duration(kart_adi)
            
            if reconnect_duration < 30:  # 30 saniyeden azsa bekle
                print(f"⏳ [PORT-SAĞLIK] {kart_adi.upper()} → Reconnection devam ediyor ({reconnect_duration:.1f}s) - ping atlanıyor")
                return  # Ping atma, bekle
            else:
                # 30 saniyeden fazla sürüyorsa uyarı ver ama hala ping atma
                print(f"⚠️ [PORT-SAĞLIK] {kart_adi.upper()} → Reconnection uzun sürüyor ({reconnect_duration:.1f}s) - bekliyor")
                # Yine de ping atma, reconnection worker devam etsin
                return
        
        # Ping gönder (sessiz - başarı durumunda log yok)
        if kart.ping():
            # Başarılı ping
            if kart.saglikli:
                # ✅ Recovery detection: UYARI/KRITIK'ten SAGLIKLI'ya geçiş = reconnection başarılı
                if durum.durum != SaglikDurumu.SAGLIKLI:
                    durum.son_reconnection_zamani = time.time()
                    log_success(f"{kart_adi.upper()} recovery başarılı - cooldown periyodu başladı")

                durum.son_pong_zamani = time.time()
                durum.basarisiz_ping = 0
                durum.durum = SaglikDurumu.SAGLIKLI
                return
        
        # Başarısız ping

        # ✅ COOLDOWN KONTROLÜ: Son reconnection'dan sonra 10 saniye geçmediyse ping timeout ignore et
        # ESP32 boot süreci 3-5 saniye sürdüğü için ilk ping'ler timeout alabilir
        reconnection_cooldown = 10  # saniye
        if durum.son_reconnection_zamani > 0:
            cooldown_suresi = time.time() - durum.son_reconnection_zamani
            if cooldown_suresi < reconnection_cooldown:
                print(f"⏸️  [PORT-SAĞLIK] {kart_adi.upper()} → PONG timeout (cooldown: {cooldown_suresi:.1f}s/{reconnection_cooldown}s) - ignore ediliyor")
                # Başarısızlık sayısını ARTIRMA - ESP32 boot süreci devam ediyor
                return

        durum.basarisiz_ping += 1
        gecen_sure = time.time() - durum.son_pong_zamani

        print(f"❌ [PORT-SAĞLIK] {kart_adi.upper()} → PONG alınamadı! (Başarısız: {durum.basarisiz_ping}/{self.MAX_PING_HATA})")
        
        # ✅ 5 ping başarısızlığında reconnection mekanizmasını tetikle
        if durum.basarisiz_ping >= self.MAX_PING_HATA:
            # ✅ Önce kart zaten reconnecting mi kontrol et
            if system_state.is_card_reconnecting(kart_adi):
                log_warning(f"⚠️ [PORT-SAĞLIK] {kart_adi.upper()} zaten reconnection yapıyor, duplicate reconnection atlanıyor")
                # Başarısızlık sayacını sıfırla (reconnection zaten devam ediyor)
                durum.basarisiz_ping = 0
                # Durum UYARI olarak set et (KRITIK değil, çünkü reconnection devam ediyor)
                durum.durum = SaglikDurumu.UYARI
                return

            print(f"🚨 [PORT-SAĞLIK] {kart_adi.upper()} kartı {self.MAX_PING_HATA} kere ping başarısız - RECONNECTION başlatılıyor!")
            log_system(f"{kart_adi.upper()} kartı ping başarısız - yeniden başlatılıyor")

            # ✅ Kartın kendi reconnection mekanizmasını tetikle
            # Bu USB reset + port arama + yeniden bağlanma yapacak
            threading.Thread(
                target=kart._handle_connection_error,
                daemon=True,
                name=f"{kart_adi}_reconnect_from_health"
            ).start()

            # Başarısızlık sayacını sıfırla (reconnection başlatıldı)
            durum.basarisiz_ping = 0
            # ✅ Durum UYARI olarak set et (KRITIK değil, reconnection başlatıldı)
            durum.durum = SaglikDurumu.UYARI
            return

        # Durum güncelle (sadece reconnection başlatılmadıysa)
        if gecen_sure > self.PING_ARASI_SURE * 2:
            durum.durum = SaglikDurumu.UYARI
            print(f"⚠️  [PORT-SAĞLIK] {kart_adi.upper()} → UYARI! Son pong: {gecen_sure:.1f}s önce")
        else:
            durum.durum = SaglikDurumu.SAGLIKLI
    
    def _durumlari_degerlendir(self):
        """Kart durumlarını değerlendir ve gerekirse müdahale et"""
        kritik_kartlar = []
        uyari_kartlar = []
        saglikli_kartlar = []

        # Kart durumlarını topla
        for kart_adi, durum in self.kart_durumlari.items():
            if durum.durum == SaglikDurumu.KRITIK:
                kritik_kartlar.append(kart_adi)
                log_error(f"{kart_adi.upper()} kartı kritik durumda!")
            elif durum.durum == SaglikDurumu.UYARI:
                uyari_kartlar.append(kart_adi)
            elif durum.durum == SaglikDurumu.SAGLIKLI:
                saglikli_kartlar.append(kart_adi)

        # Genel sağlık durumunu belirle
        if kritik_kartlar:
            current_status = "critical"
        elif uyari_kartlar:
            current_status = "warning"
        elif len(saglikli_kartlar) == 2:  # Her iki kart da sağlıklı
            current_status = "healthy"
        else:
            current_status = "partial"  # Bazı kartlar henüz bağlı değil

        # Durum değişmişse görsel mesaj göster
        if current_status != self._last_health_status:
            if current_status == "healthy":
                print("\n" + "="*70)
                print("✅ SİSTEM SAĞLIKLI - TÜM KARTLAR BAĞLI VE ÇALIŞIYOR")
                print("="*70)
                print(f"  🟢 MOTOR KARTI  : Bağlı ve sağlıklı")
                print(f"  🟢 SENSOR KARTI : Bağlı ve sağlıklı")
                print("="*70 + "\n")
                log_success("Sistem tamamen sağlıklı - Tüm kartlar çalışıyor")
            elif current_status == "warning":
                print(f"\n⚠️  UYARI: {', '.join([k.upper() for k in uyari_kartlar])} - Bağlantı sorunları tespit edildi\n")
            elif current_status == "critical":
                print(f"\n🚨 KRİTİK: {', '.join([k.upper() for k in kritik_kartlar])} - Acil müdahale gerekli!\n")

            self._last_health_status = current_status

        # Kritik durum varsa müdahale et
        if kritik_kartlar:
            self._kartlari_resetle(kritik_kartlar)
    
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
            print(f"🔧 [PORT-SAĞLIK] Reset operasyonu bitiriliyor... (ID: {operation_id}, Success: {reset_success})")
            log_system(f"Reset operasyonu bitiriliyor: {operation_id} - Success: {reset_success}")
            system_state.finish_reset_operation(operation_id, reset_success)
            print(f"✅ [PORT-SAĞLIK] Reset operasyonu bitirildi")
            log_system("Reset operasyonu bitirildi")
            
            if reset_success:
                # Sistem durumu RECONNECTING oldu, şimdi portları yeniden bağla
                print(f"⏳ [PORT-SAĞLIK] USB reset sonrası stabilizasyon bekleniyor (8 saniye)...")
                log_system("USB reset sonrası stabilizasyon bekleniyor...")
                time.sleep(8)  # Embedded sistemlerin tamamen hazır olması için
                print(f"✅ [PORT-SAĞLIK] Stabilizasyon tamamlandı")
                
                # Portları yeniden bağla
                print(f"🔍 [PORT-SAĞLIK] Portlar yeniden aranıyor...")
                log_system("Portlar yeniden aranıyor...")
                
                try:
                    basarili, mesaj, portlar = self.port_yonetici.baglan(
                        try_usb_reset=False,  # Zaten reset yaptık
                        max_retries=2,  # Daha fazla deneme
                        kritik_kartlar=["motor", "sensor"]
                    )
                    print(f"📊 [PORT-SAĞLIK] Port arama sonucu: Başarılı={basarili}, Mesaj={mesaj}, Portlar={portlar}")
                    log_system(f"Port arama sonucu: {basarili} - {mesaj}")
                    
                    if basarili:
                        print(f"✅ [PORT-SAĞLIK] Portlar başarıyla yeniden bağlandı: {portlar}")
                        log_success(f"Portlar yeniden bağlandı: {portlar}")
                        self._durumlari_sifirla()
                        
                        # Kartları yeniden başlat
                        print(f"🔄 [PORT-SAĞLIK] Kartları yeniden başlatma işlemi başlıyor...")
                        self._kartlari_yeniden_baslat(portlar)
                        print(f"✅ [PORT-SAĞLIK] Kartlar yeniden başlatıldı")
                        
                        # Sistem durumunu NORMAL'e döndür
                        system_state.set_system_state(SystemState.NORMAL, "Port sağlık servisi reset tamamlandı")
                        print(f"✅ [PORT-SAĞLIK] Sistem NORMAL duruma döndü")
                    else:
                        print(f"❌ [PORT-SAĞLIK] Port yeniden bağlantı hatası: {mesaj}")
                        log_error(f"Port yeniden bağlantı hatası: {mesaj}")
                        
                        # Kartları error durumuna al
                        for card in kritik_kartlar:
                            system_state.set_card_state(card, CardState.ERROR, "Reset sonrası port bulunamadı")
                
                except Exception as port_error:
                    print(f"❌ [PORT-SAĞLIK] Port arama hatası: {port_error}")
                    log_error(f"Port arama hatası: {port_error}")
                    import traceback
                    traceback.print_exc()
                    
                    # Kartları error durumuna al
                    for card in kritik_kartlar:
                        system_state.set_card_state(card, CardState.ERROR, f"Port arama hatası: {port_error}")
            
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
        Kartları yeniden başlat - DÜZELTİLMİŞ - _try_connect_to_port() kullanır
        
        Args:
            portlar: Port bilgileri (örn: {"motor": "/dev/ttyUSB0", "sensor": "/dev/ttyUSB1"})
        """
        try:
            print("🔄 [PORT-SAĞLIK] Kartlar yeniden başlatılıyor...")
            print("📋 [PORT-SAĞLIK] Sıralama: SENSOR ÖNCE, MOTOR SONRA")
            
            # ÖNCE SENSOR KARTI
            if "sensor" in portlar:
                print(f"  🔧 Sensor kartı: {portlar['sensor']}")
                # Önce mevcut thread'leri temizle
                self.sensor_karti.dinlemeyi_durdur()
                time.sleep(0.5)
                
                # Port ata
                self.sensor_karti.port_adi = portlar["sensor"]
                self.sensor_karti._first_connection = True
                
                # ✅ _try_connect_to_port() ile bağlan (port açma + thread başlatma)
                if self.sensor_karti._try_connect_to_port():
                    print(f"  ✅ Sensor kartı bağlandı: {portlar['sensor']}")
                    
                    # Sensor kartı için reset komutu gönder
                    time.sleep(0.5)
                    print(f"  🔄 Sensor kartı resetleniyor...")
                    self.sensor_karti.reset()
                    time.sleep(2)
                    print(f"  ✅ Sensor kartı hazır")
                else:
                    print(f"  ❌ Sensor portu açılamadı!")
            
            # SENSOR KARTI HAZIR OLDUKTAN SONRA MOTOR KARTI
            if "motor" in portlar:
                # Sensor kartının hazır olmasını bekle
                if "sensor" in portlar:
                    print(f"  ⏳ Sensor kartının hazır olması bekleniyor...")
                    time.sleep(3)
                    print(f"  ✅ Sensor kartı hazır, motor kartı başlatılıyor...")
                
                # Motor kartı için ek bekleme
                print(f"  ⏳ Motor kartı boot süreci için ek bekleme...")
                time.sleep(2)
                
                print(f"  🔧 Motor kartı: {portlar['motor']}")
                # Önce mevcut thread'leri temizle
                self.motor_karti.dinlemeyi_durdur()
                time.sleep(0.5)
                
                # Port ata
                self.motor_karti.port_adi = portlar["motor"]
                self.motor_karti._first_connection = True
                
                # ✅ _try_connect_to_port() ile bağlan (port açma + thread başlatma)
                if self.motor_karti._try_connect_to_port():
                    print(f"  ✅ Motor kartı bağlandı: {portlar['motor']}")
                    
                    # Motor parametrelerini gönder
                    time.sleep(1)
                    print(f"  🔄 Motor parametreleri gönderiliyor...")
                    self.motor_karti.parametre_gonder()
                    time.sleep(0.5)
                    
                    # Motor kartını resetle
                    print(f"  🔄 Motor kartı resetleniyor...")
                    self.motor_karti.reset()
                    time.sleep(2)
                    
                    # Motorları aktif et
                    print(f"  🔄 Motorlar aktif ediliyor...")
                    self.motor_karti.motorlari_aktif_et()
                    time.sleep(1)
                    
                    print(f"  ✅ Motor kartı hazır")
                else:
                    print(f"  ❌ Motor portu açılamadı!")
            
            # Kartların stabilizasyonunu bekle
            print(f"⏳ [PORT-SAĞLIK] Kartların stabilizasyonu için 5 saniye bekleniyor...")
            time.sleep(5)
            
            # Durumları sıfırla
            self._durumlari_sifirla()
            
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
