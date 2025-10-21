"""
sensor_karti.py - Güvenli ve profesyonel versiyon
Tüm mevcut API korundu, sadece internal iyileştirmeler yapıldı
"""

import threading
import queue
import time
import serial
from typing import Optional, Callable
from contextlib import contextmanager

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
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
        self._reconnect_lock = threading.Lock()
        self._is_reconnecting = False
        
        # Hata takibi
        self._connection_attempts = 0
        self._consecutive_errors = 0
        self._last_error_time = 0
        
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
            self.dinlemeyi_baslat()
            return True
        else:
            log_warning(f"{self.cihaz_adi} porta bağlanamadı: {self.port_adi}")
            return False

    def _auto_find_port(self) -> bool:
        """Otomatik port bulma"""
        try:
            basarili, mesaj, portlar = self.port_yoneticisi.baglan(cihaz_adi=self.cihaz_adi)
            
            if basarili and self.cihaz_adi in portlar:
                self.port_adi = portlar[self.cihaz_adi]
                log_success(f"{self.cihaz_adi} port bulundu: {self.port_adi}")
                
                if self._try_connect_to_port():
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
        self._safe_queue_put("reset", None)
    
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

    def ping(self):
        """Ping - sadece mevcut bağlantıyı test et, port arama yapma"""
        if not self._is_port_ready():
            log_warning(f"{self.cihaz_adi} port hazır değil - ping atlanıyor")
            return False
        
        # Mevcut bağlantıyı test et
        self.saglikli = False
        self._safe_queue_put("ping", None)
        
        # Ping zamanını hemen kaydet (reset bypass için)
        self._last_ping_time = time.time()
        log_system(f"{self.cihaz_adi} ping gönderildi - zaman: {self._last_ping_time:.1f}")
        
        time.sleep(self.PING_TIMEOUT)
        
        if not self.saglikli:
            log_warning(f"{self.cihaz_adi} ping başarısız - port arama yapılmıyor")
            # PORT ARAMA YAPMA! Sadece sağlık durumunu false yap
            return False
        
        log_system(f"{self.cihaz_adi} ping başarılı")
        return True

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
                # Eski portu kapat
                if self.seri_nesnesi and self.seri_nesnesi.is_open:
                    self.seri_nesnesi.close()
                    time.sleep(0.5)
                
                # Yeni port aç
                self.seri_nesnesi = serial.Serial(
                    self.port_adi, 
                    baudrate=115200, 
                    timeout=1,
                    write_timeout=1
                )
                
                log_success(f"{self.cihaz_adi} port açıldı: {self.port_adi}")
                self.saglikli = True
                self._consecutive_errors = 0
            return True
                
        except serial.SerialException as e:
            log_error(f"{self.cihaz_adi} port hatası: {e}")
            self.seri_nesnesi = None
            self.saglikli = False
            return False

    def dinlemeyi_baslat(self):
        """Thread başlatma - iyileştirilmiş"""
        with self._port_lock:
            if self.running:
                return
            
            self.running = True
            self._cleanup_threads()
            
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
            
            self.listen_thread.start()
            self.write_thread.start()
            
            log_system(f"{self.cihaz_adi} thread'leri başlatıldı")

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
        
        while self.running:
            try:
                # Komut al
                try:
                    command, data = self.write_queue.get(timeout=1)
                except queue.Empty:
                    continue

                if command == "exit":
                    break
                
                # Port kontrolü
                if not self._is_port_ready():
                    time.sleep(0.1)
                    continue
                
                # Komut gönder
                if command in komutlar:
                    self.seri_nesnesi.write(komutlar[command](data) if callable(komutlar[command]) else komutlar[command])
                    self.seri_nesnesi.flush()
                
            except (serial.SerialException, OSError) as e:
                log_error(f"{self.cihaz_adi} yazma hatası: {e}")
                self._handle_connection_error()
                break
            except Exception as e:
                log_exception(f"{self.cihaz_adi} yazma thread hatası", exc_info=(type(e), e, e.__traceback__))

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
                
                # Veri oku
                if waiting > 0:
                    data = self.seri_nesnesi.readline().decode(errors='ignore').strip()
                    if data:
                        self._consecutive_errors = 0  # Başarılı okuma
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
        """Mesaj işleme"""
        if not message or not message.isprintable():
            return
        
        message_lower = message.lower()
        
        if message_lower == "pong":
            self.saglikli = True
        elif message_lower == "resetlendi":
            log_warning(f"{self.cihaz_adi} kart resetlendi")

            
            # İlk bağlantıda gelen reset mesajını bypass et
            if self._first_connection:
                log_system(f"{self.cihaz_adi} - İlk bağlantı reset mesajı, bypass ediliyor")
                self._first_connection = False
                self.saglikli = True
                return
            
            # Seçici bypass: Sadece gömülü sistemin otomatik resetini bypass et
            # Fiziksel bağlantı sorunlarında hala reset yap
            current_time = time.time()
            time_since_ping = current_time - self._last_ping_time
            
            if time_since_ping < 30:  # Son 30 saniye içinde ping alındıysa
                # Gömülü sistem reseti - bypass et
                log_warning(f"{self.cihaz_adi} - Gömülü sistem reseti tespit edildi, bypass ediliyor (ping: {time_since_ping:.1f}s önce)")
            else:
                # Ping alınmamışsa, fiziksel bağlantı sorunu
                log_warning(f"{self.cihaz_adi} - Fiziksel bağlantı sorunu tespit edildi, reset yapılıyor (ping: {time_since_ping:.1f}s önce)")
                self.saglikli = False
                time.sleep(2)
                self._handle_connection_error()
        elif self.callback:
            try:
                self.callback(message)
            except Exception as e:
                log_error(f"{self.cihaz_adi} callback hatası: {e}")

    def _handle_connection_error(self):
        """Bağlantı hatası yönetimi - duplicate önleme"""
        # Double-check locking pattern
        if self._is_reconnecting:
            return
        
        with self._reconnect_lock:
            if self._is_reconnecting:
                return
            self._is_reconnecting = True
        
        try:
            log_system(f"{self.cihaz_adi} bağlantı hatası yönetimi")
            
            # Thread içinden çağrılıyorsa, thread'leri durdurmayı atla
            current_thread = threading.current_thread()
            if current_thread in [self.listen_thread, self.write_thread]:
                # Sadece flag'i kapat, join yapmaya çalışma
                self.running = False
            else:
                # Dışarıdan çağrılıyorsa normal durdur
                self.dinlemeyi_durdur()
            
            # Portu güvenli kapat
            with self._port_lock:
                if self.seri_nesnesi:
                    try:
                        if self.seri_nesnesi.is_open:
                            self.seri_nesnesi.close()
                    except (OSError, serial.SerialException):
                        # Port zaten kapanmış veya erişilemiyor
                        pass
                self.seri_nesnesi = None
                self.saglikli = False
            
            # Yeniden bağlanma thread'i başlat
            threading.Thread(
                target=self._reconnect_worker, 
                daemon=True,
                name=f"{self.cihaz_adi}_reconnect"
            ).start()
            
        except Exception as e:
            log_exception(f"{self.cihaz_adi} hata yönetimi başarısız", exc_info=(type(e), e, e.__traceback__))
        finally:
            pass

    def _reconnect_worker(self):
        """Yeniden bağlanma worker'ı - exponential backoff"""
        attempts = 0
        base_delay = self.RETRY_BASE_DELAY
        
        try:
            while attempts < self.MAX_RETRY:
                attempts += 1
                delay = min(base_delay * (2 ** (attempts - 1)), self.MAX_RETRY_DELAY)
                
                log_system(f"{self.cihaz_adi} yeniden bağlanma {attempts}/{self.MAX_RETRY}")
                
                if self._auto_find_port():
                    self._connection_attempts = 0
                    log_success(f"{self.cihaz_adi} yeniden bağlandı")
                    return

                time.sleep(delay)
            
            log_error(f"{self.cihaz_adi} yeniden bağlanamadı")
            
        finally:
            with self._reconnect_lock:
                self._is_reconnecting = False

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