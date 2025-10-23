"""
sensor_karti.py - Güvenli ve profesyonel versiyon
Tüm mevcut API korundu, sadece internal iyileştirmeler yapıldı
"""

import threading
import queue
import time
import serial
import subprocess
from pathlib import Path
from typing import Optional, Callable
from contextlib import contextmanager

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.makine.seri.system_state_manager import system_state, CardState, SystemState
from rvm_sistemi.utils.logger import (
    log_sensor, log_error, log_success, log_warning, 
    log_system, log_exception, log_thread_error
)


class SensorKart:
    """
    Sensor kartı sınıfı - Thread-safe ve production-ready
    Geriye uyumlu, tüm mevcut metodlar korundu
    """
    
    # Konfigürasyon sabitleri
    MAX_RETRY = 10
    RETRY_BASE_DELAY = 2
    MAX_RETRY_DELAY = 30
    PING_TIMEOUT = 0.3
    QUEUE_MAX_SIZE = 100
    MAX_CONSECUTIVE_ERRORS = 5
    
    def __init__(self, port_adi=None, callback=None, cihaz_adi="sensor"):
        """
        Sensor kartı başlatıcı
        
        Args:
            port_adi: Seri port adı (opsiyonel)
            callback: Mesaj callback fonksiyonu
            cihaz_adi: Cihaz adı
        """
        self.port_adi = port_adi
        self.seri_nesnesi = None
        self.callback = callback
        self.cihaz_adi = cihaz_adi
        self.port_yoneticisi = KartHaberlesmeServis()
        
        # Reset bypass için ping zamanı takibi
        self._last_ping_time = time.time()  # Başlangıç zamanı
        self._first_connection = True  # İlk bağlantı takibi
        
        # Thread yönetimi
        self.running = False
        self.listen_thread = None
        self.write_thread = None
        self.write_queue = queue.Queue(maxsize=self.QUEUE_MAX_SIZE)
        
        # Sağlık durumu
        self.saglikli = False
        
        # Thread safety için lock'lar
        self._port_lock = threading.RLock()
        
        # Hata takibi
        self._connection_attempts = 0
        self._consecutive_errors = 0
        self._last_error_time = 0
        
        # System state manager'a kaydol
        system_state.set_card_state(self.cihaz_adi, CardState.DISCONNECTED, "Başlatıldı")
        
        # İlk bağlantıyı başlat
        self._ilk_baglanti()

    def _ilk_baglanti(self):
        """İlk bağlantı kurulumu - thread-safe"""
        with self._port_lock:
            log_system(f"{self.cihaz_adi} ilk bağlantı kuruluyor...")
            
            # Port verilmişse önce onu dene
            if self.port_adi and self._try_connect_to_port():
                return True
            
            # Otomatik port bulma
            if self._auto_find_port():
                return True
            
            # Bulunamazsa arka planda aramaya devam et
            self._start_background_search()
            return False

    def _try_connect_to_port(self) -> bool:
        """Belirtilen porta bağlanmayı dene"""
        if self.portu_ac():
            log_success(f"{self.cihaz_adi} porta bağlandı: {self.port_adi}")
            system_state.set_card_state(self.cihaz_adi, CardState.CONNECTED, f"Port açıldı: {self.port_adi}")
            self.dinlemeyi_baslat()
            return True
        else:
            log_warning(f"{self.cihaz_adi} porta bağlanamadı: {self.port_adi}")
            system_state.set_card_state(self.cihaz_adi, CardState.ERROR, f"Port açılamadı: {self.port_adi}")
            return False

    def _auto_find_port(self) -> bool:
        """Otomatik port bulma"""
        try:
            basarili, mesaj, portlar = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)
            
            if basarili and self.cihaz_adi in portlar:
                self.port_adi = portlar[self.cihaz_adi]
                log_success(f"{self.cihaz_adi} port bulundu: {self.port_adi}")
                
                if self._try_connect_to_port():
                    # Thread durumunu kontrol et
                    if self.thread_durumu_kontrol():
                        log_system(f"{self.cihaz_adi} _auto_find_port - thread'ler başarıyla başlatıldı")
                    else:
                        log_warning(f"{self.cihaz_adi} _auto_find_port - thread'ler başlatılamadı")
                    return True
            else:
                log_warning(f"{self.cihaz_adi} otomatik port bulunamadı: {mesaj}")
                
        except Exception as e:
            log_error(f"{self.cihaz_adi} port arama hatası: {e}")
            
        return False

    def _start_background_search(self):
        """Arka planda port arama başlat - sonsuz döngü önlendi"""
        def search_worker():
            attempts = 0
            base_delay = self.RETRY_BASE_DELAY
            
            while attempts < self.MAX_RETRY:
                # Bağlantı varsa çık
                with self._port_lock:
                    if self.seri_nesnesi and self.seri_nesnesi.is_open:
                        return
                
                attempts += 1
                delay = min(base_delay * (2 ** (attempts - 1)), self.MAX_RETRY_DELAY)
                
                log_system(f"{self.cihaz_adi} port arama {attempts}/{self.MAX_RETRY}")
                
                if self._auto_find_port():
                    self._connection_attempts = 0
                    # Thread durumunu kontrol et
                    if self.thread_durumu_kontrol():
                        log_system(f"{self.cihaz_adi} _start_background_search - thread'ler başarıyla başlatıldı")
                    else:
                        log_warning(f"{self.cihaz_adi} _start_background_search - thread'ler başlatılamadı")
                    return
                
                time.sleep(delay)
            
            log_error(f"{self.cihaz_adi} maksimum arama denemesi aşıldı")
        
        thread = threading.Thread(target=search_worker, daemon=True, name=f"{self.cihaz_adi}_search")
        thread.start()

    # =============== MEVCUT PUBLIC METODLAR (DEĞİŞMEDİ) ===============
    
    def loadcell_olc(self): 
        self._safe_queue_put("loadcell_olc", None)
    
    def teach(self): 
        self._safe_queue_put("teach", None)
    
    def led_ac(self): 
        self._safe_queue_put("led_ac", None)
    
    def led_full_ac(self): 
        self._safe_queue_put("ledfull_ac", None)
    
    def led_full_kapat(self): 
        self._safe_queue_put("ledfull_kapat", None)
    
    def led_kapat(self): 
        self._safe_queue_put("led_kapat", None)
    
    def led_pwm(self, deger): 
        self._safe_queue_put("led_pwm", deger)
    
    def tare(self): 
        self._safe_queue_put("tare", None)
    
    def reset(self): 
        log_system(f"{self.cihaz_adi} reset komutu gönderiliyor...")
        # Write thread'in çalışıp çalışmadığını kontrol et
        if not (self.write_thread and self.write_thread.is_alive()):
            log_error(f"{self.cihaz_adi} write thread çalışmıyor - reset komutu gönderilemiyor")
            return False
        
        self._safe_queue_put("reset", None)
        log_system(f"{self.cihaz_adi} reset komutu queue'ya eklendi")
        return True
    
    def ezici_ileri(self): 
        self._safe_queue_put("ezici_ileri", None)
    
    def ezici_geri(self): 
        self._safe_queue_put("ezici_geri", None)
    
    def ezici_dur(self): 
        self._safe_queue_put("ezici_dur", None)
    
    def kirici_ileri(self): 
        self._safe_queue_put("kirici_ileri", None)
    
    def kirici_geri(self): 
        self._safe_queue_put("kirici_geri", None)
    
    def kirici_dur(self): 
        self._safe_queue_put("kirici_dur", None)
    
    def doluluk_oranı(self): 
        self._safe_queue_put("doluluk_oranı", None)
    
    def makine_oturum_var(self): 
        self._safe_queue_put("makine_oturum_var", None)
    
    def makine_oturum_yok(self): 
        self._safe_queue_put("makine_oturum_yok", None)
    
    def makine_bakim_modu(self): 
        self._safe_queue_put("makine_bakim_modu", None)

    # Güvenlik kartı komutları
    def ust_kilit_ac(self): 
        self._safe_queue_put("ust_kilit_ac", None)
    
    def ust_kilit_kapat(self): 
        self._safe_queue_put("ust_kilit_kapat", None)
    
    def alt_kilit_ac(self): 
        self._safe_queue_put("alt_kilit_ac", None)
    
    def alt_kilit_kapat(self): 
        self._safe_queue_put("alt_kilit_kapat", None)
    
    def ust_kilit_durum_sorgula(self): 
        self._safe_queue_put("ust_kilit_durum_sorgula", None)
    
    def alt_kilit_durum_sorgula(self): 
        self._safe_queue_put("alt_kilit_durum_sorgula", None)
    
    def bme_guvenlik(self): 
        self._safe_queue_put("bme_guvenlik", None)
    
    def manyetik_saglik(self): 
        self._safe_queue_put("manyetik_saglik", None)
    
    def fan_pwm(self, deger): 
        self._safe_queue_put("fan_pwm", deger)
    
    def bypass_modu_ac(self): 
        self._safe_queue_put("bypass_modu_ac", None)
    
    def bypass_modu_kapat(self): 
        self._safe_queue_put("bypass_modu_kapat", None)
    
    def guvenlik_role_reset(self): 
        self._safe_queue_put("guvenlik_role_reset", None)
    
    def guvenlik_kart_reset(self): 
        self._safe_queue_put("guvenlik_kart_reset", None)

    def ping(self, bypass_reconnection_check=False):
        """Ping - sadece mevcut bağlantıyı test et"""
        # Reconnect devam ediyorsa ping atma
        if not bypass_reconnection_check and system_state.is_card_reconnecting(self.cihaz_adi):
            return False

        if not self._is_port_ready():
            return False

        # Ping zamanını kaydet (reset bypass için)
        self._last_ping_time = time.time()

        # Sağlık durumunu False yap (gerçek yanıt gelene kadar)
        self.saglikli = False

        # Ping gönder
        self._safe_queue_put("ping", None)

        # PONG cevabını bekle
        ping_start = time.time()
        timeout = self.PING_TIMEOUT * 2  # 0.6 saniye

        while time.time() - ping_start < timeout:
            if self.saglikli:  # PONG geldi
                return True
            time.sleep(0.05)

        # Timeout - PONG gelmedi (sadece hata durumunda log)
        log_error(f"{self.cihaz_adi.upper()} ping timeout")
        self.saglikli = False
        return False

    def getir_saglik_durumu(self):
        """Sağlık durumu"""
        return self.saglikli

    def agirlik_olc(self):
        """Ağırlık ölçümü"""
        if not self._is_port_ready():
            return False
        
        self._safe_queue_put("loadcell_olc", None)
        return True
    
    def sds_sensorler(self):
        """SDS sensör durumları - MEVCUT METOD KORUNDU"""
        if not self._is_port_ready():
            return False
        
        self._safe_queue_put("sds_sensorler", None)
        return True

    def portu_ac(self):
        """Port açma - thread-safe"""
        if not self.port_adi:
            return False

        try:
            with self._port_lock:
                # ✅ Eski port adını sakla - self.port_adi zaten yeni port olabilir!
                old_port_path = None
                if self.seri_nesnesi and self.seri_nesnesi.is_open:
                    old_port_path = self.seri_nesnesi.port  # Gerçek eski port path

                # Eski portu kapat ve release et
                if old_port_path:
                    system_state.release_port(old_port_path, self.cihaz_adi)
                    log_system(f"{self.cihaz_adi} eski port release edildi: {old_port_path}")
                    self.seri_nesnesi.close()
                    self.seri_nesnesi = None
                    time.sleep(0.5)
                
                # Yeni port aç
                self.seri_nesnesi = serial.Serial(
                    self.port_adi,
                    baudrate=115200,
                    timeout=1,
                    write_timeout=1
                )

                log_success(f"{self.cihaz_adi} port açıldı: {self.port_adi}")

                # Port sahipliğini claim et
                if not system_state.claim_port(self.port_adi, self.cihaz_adi):
                    log_error(f"{self.cihaz_adi} port sahipliği alınamadı: {self.port_adi}")
                    self.seri_nesnesi.close()
                    self.seri_nesnesi = None
                    self.saglikli = False
                    return False

                self.saglikli = True
                self._consecutive_errors = 0
            return True
                
        except serial.SerialException as e:
            log_error(f"{self.cihaz_adi} port hatası: {e}")
            self.seri_nesnesi = None
            self.saglikli = False
            return False

    def dinlemeyi_baslat(self):
        """Thread başlatma - iyileştirilmiş - DEADLOCK FIX + ZOMBIE THREAD KONTROLÜ"""
        # Port kontrolü ve running flag ayarları lock içinde
        with self._port_lock:
            # Port açık değilse thread başlatma
            if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
                log_warning(f"{self.cihaz_adi} port açık değil - thread başlatılamıyor")
                return
            
            # ✅ ZOMBIE THREAD KONTROLÜ
            # Thread'ler "çalışıyor" görünüyorsa ama gerçekte is_alive() False ise temizle
            threads_alive = (
                (self.listen_thread and self.listen_thread.is_alive()) and
                (self.write_thread and self.write_thread.is_alive())
            )
            
            if self.running and not threads_alive:
                # Zombie thread durumu - temizle
                log_warning(f"{self.cihaz_adi} zombie thread tespit edildi - temizleniyor")
                self.running = False
                # Lock'u bırak, thread temizliği için
            elif self.running and threads_alive:
                # Thread'ler zaten çalışıyor (gerçekten alive)
                log_warning(f"{self.cihaz_adi} thread'ler zaten çalışıyor")
                return
            elif not self.running and threads_alive:
                # running=False ama thread'ler hala alive - durdur
                log_warning(f"{self.cihaz_adi} orphan thread'ler bulundu - durduruluyor")
                self.running = False
            
            # Eski thread'leri temizle
            if self.running:
                log_system(f"{self.cihaz_adi} eski thread'leri temizleniyor...")
                self.running = False
                # Lock'u bırak, thread'lerin durması için
        
        # Lock DIŞINDA thread temizliği
        if not self.running:
            time.sleep(0.5)  # Thread'lerin durması için bekle
            self._cleanup_threads()
        
        # Lock içinde running flag'i ayarla
        with self._port_lock:
            self.running = True
        
        # ✅ LOCK DIŞINDA thread'leri başlat (deadlock önleme)
        # Thread'leri başlat
        self.listen_thread = threading.Thread(
            target=self._dinle, 
            daemon=True, 
            name=f"{self.cihaz_adi}_listen"
        )
        self.write_thread = threading.Thread(
            target=self._yaz, 
            daemon=True, 
            name=f"{self.cihaz_adi}_write"
        )
        
        # Thread'leri sırayla başlat
        self.listen_thread.start()
        time.sleep(0.1)  # Listen thread'in başlaması için bekle
        self.write_thread.start()
        time.sleep(0.1)  # Write thread'in başlaması için bekle
        
        log_system(f"{self.cihaz_adi} thread'leri başlatıldı")
        
        # Thread'lerin başlamasını bekle
        time.sleep(0.5)  # Thread'lerin başlaması için bekle
        
        # Thread durumunu kontrol et ve logla
        if self.thread_durumu_kontrol():
            log_success(f"{self.cihaz_adi} thread'leri başarıyla başlatıldı")
        else:
            log_error(f"{self.cihaz_adi} thread'leri başlatılamadı - yeniden denenecek")
            # Thread'leri tekrar başlat
            self._cleanup_threads()
            time.sleep(0.5)
            self.listen_thread = threading.Thread(
                target=self._dinle, 
                daemon=True, 
                name=f"{self.cihaz_adi}_listen"
            )
            self.write_thread = threading.Thread(
                target=self._yaz, 
                daemon=True, 
                name=f"{self.cihaz_adi}_write"
            )
            self.listen_thread.start()
            time.sleep(0.1)
            self.write_thread.start()
            time.sleep(0.1)
            log_system(f"{self.cihaz_adi} thread'leri tekrar başlatıldı")

    def dinlemeyi_durdur(self):
        """Thread durdurma - güvenli"""
        with self._port_lock:
            if not self.running:
                return
                
        self.running = False
        
        # Exit sinyali gönder
        try:
            self.write_queue.put_nowait(("exit", None))
        except queue.Full:
            pass
        
        # Thread'leri bekle - kendini join etmeyi önle
        current_thread = threading.current_thread()
        for thread in [self.listen_thread, self.write_thread]:
            if thread and thread.is_alive() and thread != current_thread:
                thread.join(timeout=1)
        
        log_system(f"{self.cihaz_adi} thread'leri durduruldu")

    # =============== INTERNAL İYİLEŞTİRMELER ===============

    def _safe_queue_put(self, command, data=None):
        """Queue'ya güvenli yazma"""
        try:
            # Queue doluysa eski komutları temizle
            if self.write_queue.full():
                try:
                    self.write_queue.get_nowait()
                    log_warning(f"{self.cihaz_adi} queue dolu, eski komut atıldı")
                except queue.Empty:
                    pass
            
            self.write_queue.put((command, data), timeout=0.1)
            
        except queue.Full:
            log_error(f"{self.cihaz_adi} komut gönderilemedi: {command}")

    def _cleanup_threads(self):
        """Thread temizliği"""
        for thread in [self.listen_thread, self.write_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=0.1)
    
    def thread_durumu_kontrol(self):
        """Thread durumunu kontrol et"""
        with self._port_lock:
            listen_ok = self.listen_thread and self.listen_thread.is_alive()
            write_ok = self.write_thread and self.write_thread.is_alive()
            
            if listen_ok and write_ok:
                log_system(f"{self.cihaz_adi} thread'leri çalışıyor - Listen: {listen_ok}, Write: {write_ok}")
                return True
            else:
                log_warning(f"{self.cihaz_adi} thread durumu - Listen: {listen_ok}, Write: {write_ok}")
                # Thread'lerin neden çalışmadığını kontrol et
                if not listen_ok:
                    log_error(f"{self.cihaz_adi} listen thread çalışmıyor")
                if not write_ok:
                    log_error(f"{self.cihaz_adi} write thread çalışmıyor")
                return False

    def _is_port_ready(self) -> bool:
        """Port hazır mı?"""
        with self._port_lock:
            return (
                self.seri_nesnesi is not None
                and self.seri_nesnesi.is_open
                and self.running
            )

    def _yaz(self):
        """Yazma thread'i - optimized"""
        komutlar = self._get_komut_sozlugu()
        log_system(f"{self.cihaz_adi} write thread başlatıldı")
        
        while self.running:
            try:
                # Komut al
                try:
                    command, data = self.write_queue.get(timeout=1)
                except queue.Empty:
                    continue

                if command == "exit":
                    log_system(f"{self.cihaz_adi} write thread çıkıyor")
                    break
                
                # Port kontrolü
                if not self._is_port_ready():
                    log_warning(f"{self.cihaz_adi} write thread - port hazır değil")
                    time.sleep(0.1)
                    continue
                
                # Komut gönder (sessiz)
                if command in komutlar:
                    self.seri_nesnesi.write(komutlar[command](data) if callable(komutlar[command]) else komutlar[command])
                    self.seri_nesnesi.flush()
                
            except (serial.SerialException, OSError) as e:
                log_error(f"{self.cihaz_adi} yazma hatası: {e}")
                self._handle_connection_error()
                break
            except Exception as e:
                log_exception(f"{self.cihaz_adi} yazma thread hatası", exc_info=(type(e), e, e.__traceback__))
        
        log_system(f"{self.cihaz_adi} write thread bitti")

    def _dinle(self):
        """Dinleme thread'i - consecutive error tracking"""
        self._consecutive_errors = 0
        
        while self.running:
            try:
                if not self._is_port_ready():
                    time.sleep(0.5)
                    continue
                
                # I/O Error'a karşı güvenli port erişimi
                try:
                    waiting = self.seri_nesnesi.in_waiting
                except (OSError, serial.SerialException) as e:
                    # Port fiziksel olarak kopmuş olabilir
                    log_error(f"{self.cihaz_adi} port erişim hatası: {e}")
                    self._handle_connection_error()
                    break
                
                # Veri oku (sessiz)
                if waiting > 0:
                    data = self.seri_nesnesi.readline().decode(errors='ignore').strip()
                    if data:
                        self._consecutive_errors = 0
                        self._process_message(data)
                else:
                    time.sleep(0.05)
                
            except (serial.SerialException, OSError) as e:
                self._consecutive_errors += 1
                log_error(f"{self.cihaz_adi} okuma hatası ({self._consecutive_errors}): {e}")
                
                if self._consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    self._handle_connection_error()
                    break
                
                time.sleep(0.5)
                
            except Exception as e:
                log_exception(f"{self.cihaz_adi} dinleme hatası", exc_info=(type(e), e, e.__traceback__))
                time.sleep(1)

    def _process_message(self, message: str):
        """Mesaj işleme - Sadeleştirilmiş"""
        if not message or not message.isprintable():
            return  # Geçersiz mesajlar sessizce ignore et

        message_lower = message.lower()

        if message_lower == "pong":
            # Başarılı ping - sessiz (noise azaltma)
            self.saglikli = True
        elif message_lower == "resetlendi":
            log_warning(f"{self.cihaz_adi.upper()} kartı resetlendi")

            # İlk bağlantıda gelen reset mesajını bypass et
            if self._first_connection:
                self._first_connection = False
                self.saglikli = True
                return

            # Seçici bypass: Sadece gömülü sistemin otomatik resetini bypass et
            current_time = time.time()
            time_since_ping = current_time - self._last_ping_time

            if time_since_ping < 120:  # Son 120 saniye içinde ping alındıysa
                # Gömülü sistem reseti - bypass et
                self.saglikli = True
            else:
                # Fiziksel bağlantı sorunu
                log_warning(f"{self.cihaz_adi.upper()} - Fiziksel bağlantı sorunu, reset yapılıyor")
                self.saglikli = False
                time.sleep(2)
                self._handle_connection_error()
        elif self.callback:
            # Callback'e giden mesajları sadeleştir - sadece önemli olanları logla
            important_messages = ['agirlik', 'doluluk', 'kilitlendi', 'acildi', 'guvenlik', 'manyetik', 'bme']
            if any(imp in message_lower for imp in important_messages):
                log_system(f"SENSOR: {message}")  # Sade format
            try:
                self.callback(message)
            except Exception as e:
                log_error(f"{self.cihaz_adi} callback hatası: {e}")
        else:
            # Callback yoksa ve tanınmayan mesaj - sessiz (noise azaltma)
            pass

    def _try_usb_reset(self, port_path: str) -> bool:
        """
        USB portunu fiziksel reset et
        
        Args:
            port_path: Reset atılacak port yolu
            
        Returns:
            bool: Reset başarılı mı?
        """
        try:
            script_path = Path(__file__).parent / "usb_reset_helper.sh"
            
            if not script_path.exists():
                log_warning(f"USB reset scripti bulunamadı: {script_path}")
                return False
            
            log_system(f"USB reset deneniyor: {port_path}")
            result = subprocess.run(
                ['sudo', str(script_path), port_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                log_success(f"USB reset başarılı: {port_path}")
                time.sleep(2)  # Driver yeniden yüklenmesini bekle
                return True
            else:
                log_warning(f"USB reset başarısız: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            log_error(f"USB reset timeout: {port_path}")
            return False
        except Exception as e:
            log_error(f"USB reset hatası: {e}")
            return False

    def _handle_connection_error(self):
        """Bağlantı hatası yönetimi - System State Manager ile - İYİLEŞTİRİLMİŞ"""

        # ✅ ÖNCELİKLE reconnection durumu kontrol et - race condition önlemi
        # Eğer başka bir thread zaten reconnection başlattıysa, bu thread sessizce çıkar
        if not system_state.can_start_reconnection(self.cihaz_adi):
            log_system(f"{self.cihaz_adi} reconnection başka bir thread tarafından yönetiliyor, bu thread sonlandırılıyor")
            return

        # ✅ USB reset devam ediyorsa bekle (diğer kartın reset'i bitsin)
        if system_state.get_system_state() == SystemState.USB_RESETTING:
            log_system(f"{self.cihaz_adi} USB reset devam ediyor, bekleniyor...")
            # USB reset bitene kadar bekle (max 90 saniye)
            wait_start = time.time()
            while system_state.get_system_state() == SystemState.USB_RESETTING:
                if time.time() - wait_start > 90:
                    log_error(f"{self.cihaz_adi} USB reset timeout (90s), reconnection iptal ediliyor")
                    return
                time.sleep(0.5)

            log_system(f"{self.cihaz_adi} USB reset bitti, reconnection başlatılıyor...")
            time.sleep(1)  # Reset sonrası stabilizasyon

        # ✅ Reconnection başlat (TEKRAR KONTROL ET - wait sırasında başka thread başlatmış olabilir)
        if not system_state.start_reconnection(self.cihaz_adi, "I/O Error"):
            log_system(f"{self.cihaz_adi} reconnection başlatılamadı (başka thread zaten başlattı)")
            return
        
        try:
            log_system(f"{self.cihaz_adi} bağlantı hatası yönetimi")
            
            # 1. Thread'leri tam olarak durdur
            self.running = False  # Tüm thread'lere dur sinyali
            
            # 2. Thread'lerin bitmesini bekle (kendini join etmemeye dikkat)
            current_thread = threading.current_thread()
            
            if hasattr(self, 'listen_thread') and self.listen_thread:
                if self.listen_thread != current_thread and self.listen_thread.is_alive():
                    log_system(f"{self.cihaz_adi} listen thread'i bekleniyor...")
                    self.listen_thread.join(timeout=2.0)
                    
            if hasattr(self, 'write_thread') and self.write_thread:
                if self.write_thread != current_thread and self.write_thread.is_alive():
                    # Exit sinyali gönder
                    try:
                        self.write_queue.put_nowait(("exit", None))
                    except queue.Full:
                        pass
                    log_system(f"{self.cihaz_adi} write thread'i bekleniyor...")
                    self.write_thread.join(timeout=2.0)
            
            # 3. Portu güvenli kapat
            with self._port_lock:
                # ✅ CRITICAL FIX: Port release her durumda yapılmalı (is_open check olmadan)
                # Çünkü I/O error sonrası serial object kapalı olabilir ama registry'de hala claimed
                if self.port_adi:
                    system_state.release_port(self.port_adi, self.cihaz_adi)

                if self.seri_nesnesi:
                    try:
                        if self.seri_nesnesi.is_open:
                            # ✅ Bekleyen okuma/yazmayı iptal et
                            try:
                                self.seri_nesnesi.cancel_read()
                                self.seri_nesnesi.cancel_write()
                            except AttributeError:
                                pass  # cancel_read/write her zaman mevcut olmayabilir
                            self.seri_nesnesi.close()
                    except (OSError, serial.SerialException) as e:
                        log_warning(f"{self.cihaz_adi} port kapatma hatası: {e}")
                        pass
                self.seri_nesnesi = None
                self.saglikli = False

            # 3.5. Queue'yu temizle - stale komutları önle
            cleared_count = 0
            try:
                while not self.write_queue.empty():
                    self.write_queue.get_nowait()
                    cleared_count += 1
            except queue.Empty:
                pass

            if cleared_count > 0:
                log_system(f"{self.cihaz_adi} write queue temizlendi ({cleared_count} stale komut silindi)")

            # 4. USB Reset dene (opsiyonel) - SADECE USB_RESETTING durumunda değilse
            if self.port_adi and system_state.get_system_state() != SystemState.USB_RESETTING:
                self._try_usb_reset(self.port_adi)
            
            # 5. Reconnection thread başlat (tek seferlik)
            thread_name = f"{self.cihaz_adi}_reconnect"
            reconnect_thread = threading.Thread(
                target=self._reconnect_worker, 
                daemon=True,
                name=thread_name
            )
            
            # Thread'i system state manager'a kaydet
            if system_state.register_thread(thread_name, reconnect_thread):
                reconnect_thread.start()
            else:
                # Thread kaydedilemedi, reconnection'ı bitir
                system_state.finish_reconnection(self.cihaz_adi, False)
            
        except Exception as e:
            log_exception(f"{self.cihaz_adi} hata yönetimi başarısız", exc_info=(type(e), e, e.__traceback__))
            system_state.finish_reconnection(self.cihaz_adi, False)

    def _reconnect_worker(self):
        """Yeniden bağlanma worker'ı - System State Manager ile - İYİLEŞTİRİLMİŞ"""
        thread_name = f"{self.cihaz_adi}_reconnect"
        attempts = 0
        base_delay = self.RETRY_BASE_DELAY
        
        try:
            while attempts < self.MAX_RETRY:
                # Sistem durumu kontrolü
                if system_state.get_system_state() == SystemState.EMERGENCY:
                    log_warning(f"{self.cihaz_adi} reconnection iptal edildi - Emergency mode")
                    break
                
                attempts += 1
                delay = min(base_delay * (2 ** (attempts - 1)), self.MAX_RETRY_DELAY)
                
                log_system(f"{self.cihaz_adi} yeniden bağlanma {attempts}/{self.MAX_RETRY}")
                
                if self._auto_find_port():
                    # ✅ Port bulundu, thread'ler başladı
                    # ESP32 boot için yeterli bekleme (boot mesajları + firmware başlatma)
                    log_system(f"{self.cihaz_adi} ESP32 boot ve firmware başlatması bekleniyor...")
                    time.sleep(3.0)  # ESP32'nin tam boot olması için 3 saniye

                    # ✅ Ping/Pong ile sensor kartını doğrula
                    log_system(f"{self.cihaz_adi} reconnection doğrulaması - ping/pong testi...")
                    sensor_saglikli = False

                    for dogrulama_denemesi in range(3):
                        if self.ping(bypass_reconnection_check=True):  # ✅ Reconnection check bypass ile ping gönder
                            log_success(f"{self.cihaz_adi} doğrulama başarılı - PONG alındı")
                            sensor_saglikli = True
                            break
                        else:
                            log_warning(f"{self.cihaz_adi} doğrulama denemesi {dogrulama_denemesi + 1}/3 - PONG alınamadı")
                            time.sleep(1.0)  # Denemeler arası bekleme artırıldı

                    if not sensor_saglikli:
                        log_error(f"{self.cihaz_adi} doğrulama başarısız - ping/pong çalışmıyor")
                        # ✅ Portu kapat ve release et, sonra tekrar dene
                        log_system(f"{self.cihaz_adi} validation başarısız - port kapatılıyor ve release ediliyor")
                        self.dinlemeyi_durdur()
                        if self.seri_nesnesi and self.seri_nesnesi.is_open:
                            self.seri_nesnesi.close()
                        self.port_yonetici.release_port(self.port_adi, self.cihaz_adi)
                        continue  # Reconnection'ı tekrar dene

                    # ✅ Başarılı, bağlantı kuruldu
                    self._connection_attempts = 0

                    log_success(f"{self.cihaz_adi} yeniden bağlandı")

                    # Thread durumunu kontrol et ve logla
                    if self.thread_durumu_kontrol():
                        log_system(f"{self.cihaz_adi} reconnection tamamlandı - thread'ler çalışıyor")
                    else:
                        log_warning(f"{self.cihaz_adi} reconnection tamamlandı ama thread'ler çalışmıyor")

                    # Başarılı reconnection
                    system_state.finish_reconnection(self.cihaz_adi, True)
                    return

                log_warning(f"{self.cihaz_adi} bağlanamadı, {delay}s bekliyor...")
                time.sleep(delay)
            
            log_error(f"{self.cihaz_adi} yeniden bağlanamadı ({self.MAX_RETRY} deneme)")

            # ✅ Zombie port claim'i temizle - başarısız reconnection'dan sonra
            if self.port_adi:
                log_system(f"{self.cihaz_adi} reconnection başarısız - zombie port claim temizleniyor: {self.port_adi}")
                self.port_yonetici.release_port(self.port_adi, self.cihaz_adi)
                self.port_adi = None

            # Başarısız reconnection
            system_state.finish_reconnection(self.cihaz_adi, False)

        except Exception as e:
            log_exception(f"{self.cihaz_adi} reconnection worker hatası", exc_info=(type(e), e, e.__traceback__))

            # ✅ Exception durumunda da zombie port claim'i temizle
            if self.port_adi:
                log_system(f"{self.cihaz_adi} exception sonrası zombie port claim temizleniyor: {self.port_adi}")
                try:
                    self.port_yonetici.release_port(self.port_adi, self.cihaz_adi)
                    self.port_adi = None
                except Exception:
                    pass  # En azından finish_reconnection çağrılsın

            system_state.finish_reconnection(self.cihaz_adi, False)
        finally:
            # Thread kaydını sil
            system_state.unregister_thread(thread_name)
            log_system(f"{self.cihaz_adi} reconnect worker sonlandı")

    def _get_komut_sozlugu(self):
        """Komut sözlüğü - MEVCUT KOMUTLAR KORUNDU"""
        return {
            # Loadcell
            "loadcell_olc": b"lo\n",
            "teach": b"gst\n",
            "tare": b"lst\n",
            
            # LED
            "led_ac": b"as\n",
            "led_kapat": b"ad\n",
            "ledfull_ac": b"la\n",
            "ledfull_kapat": b"ls\n",
            "led_pwm": lambda val: f"l:{val if val else 0}\n".encode(),
            
            # Ezici/Kırıcı
            "ezici_ileri": b"ei\n",
            "ezici_geri": b"eg\n",
            "ezici_dur": b"ed\n",
            "kirici_ileri": b"ki\n",
            "kirici_geri": b"kg\n",
            "kirici_dur": b"kd\n",
            
            # Durum
            "doluluk_oranı": b"do\n",
            "sds_sensorler": b"sds\n",  # SDS KOMUTU KORUNDU
            
            # Makine
            "makine_oturum_var": b"mov\n",
            "makine_oturum_yok": b"moy\n",
            "makine_bakim_modu": b"mb\n",
            
            # Güvenlik
            "ust_kilit_ac": b"#uka\n",
            "ust_kilit_kapat": b"#ukk\n",
            "alt_kilit_ac": b"#aka\n",
            "alt_kilit_kapat": b"#akk\n",
            "ust_kilit_durum_sorgula": b"#msud\n",
            "alt_kilit_durum_sorgula": b"#msad\n",
            "bme_guvenlik": b"#bme\n",
            "manyetik_saglik": b"#mesd\n",
            "fan_pwm": lambda val: f"#f:{val if val else 0}\n".encode(),
            "bypass_modu_ac": b"#bypa\n",
            "bypass_modu_kapat": b"#bypp\n",
            "guvenlik_role_reset": b"#gr\n",
            "guvenlik_kart_reset": b"#reset\n",
            
            # Sistem
            "ping": b"ping\n",
            "reset": b"reset\n"
        }