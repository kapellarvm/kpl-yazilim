"""
motor_karti.py - Güvenli ve profesyonel versiyon
Tüm mevcut API korundu, sadece internal iyileştirmeler yapıldı
"""

import threading
import queue
import time
import serial
from typing import Optional, Callable

from rvm_sistemi.makine.seri.port_yonetici import KartHaberlesmeServis
from rvm_sistemi.utils.logger import (
    log_motor, log_error, log_success, log_warning, 
    log_system, log_exception, log_thread_error
)


class MotorKart:
    """
    Motor kartı sınıfı - Thread-safe ve production-ready
    Geriye uyumlu, tüm mevcut metodlar korundu
    """
    
    # Konfigürasyon sabitleri
    MAX_RETRY = 10
    RETRY_BASE_DELAY = 2
    MAX_RETRY_DELAY = 30
    PING_TIMEOUT = 0.3
    QUEUE_MAX_SIZE = 100
    MAX_CONSECUTIVE_ERRORS = 5
    
    def __init__(self, port_adi=None, callback=None, cihaz_adi="motor"):
        """
        Motor kartı başlatıcı
        
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
        
        # Motor parametreleri (MEVCUT DEĞİŞKENLER KORUNDU)
        self.konveyor_hizi = 35
        self.yonlendirici_hizi = 100
        self.klape_hizi = 200
        self.klape_flag = False
        
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
                time.sleep(1)
                self.parametre_gonder()
                return True
            
            # Otomatik port bulma
            if self._auto_find_port():
                time.sleep(1)
                self.parametre_gonder()
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
                    time.sleep(1)
                    self.parametre_gonder()
                    self._connection_attempts = 0
                    return
                
                time.sleep(delay)
            
            log_error(f"{self.cihaz_adi} maksimum arama denemesi aşıldı")
        
        thread = threading.Thread(target=search_worker, daemon=True, name=f"{self.cihaz_adi}_search")
        thread.start()

    # =============== MEVCUT PUBLIC METODLAR (DEĞİŞMEDİ) ===============

    # Motor parametreleri
    def parametre_gonder(self):
        self._safe_queue_put("parametre_gonder", None)

    def parametre_degistir(self, konveyor=None, yonlendirici=None, klape=None):
        """Motor parametrelerini değiştir"""
        if konveyor is not None:
            self.konveyor_hizi = konveyor
        if yonlendirici is not None:
            self.yonlendirici_hizi = yonlendirici
        if klape is not None:
            self.klape_hizi = klape
        self.parametre_gonder()

    def konveyor_hiz_ayarla(self, hiz):
        self.konveyor_hizi = hiz
        self.parametre_gonder()

    def yonlendirici_hiz_ayarla(self, hiz):
        self.yonlendirici_hizi = hiz
        self.parametre_gonder()

    def klape_hiz_ayarla(self, hiz):
        self.klape_hizi = hiz
        self.parametre_gonder()

    def reset(self):
        self._safe_queue_put("reset", None)

    # Motor kontrol
    def motorlari_aktif_et(self):
        self._safe_queue_put("motorlari_aktif_et", None)

    def motorlari_iptal_et(self):
        self._safe_queue_put("motorlari_iptal_et", None)

    # Konveyör
    def konveyor_ileri(self):
        self._safe_queue_put("konveyor_ileri", None)

    def konveyor_geri(self):
        self._safe_queue_put("konveyor_geri", None)

    def konveyor_dur(self):
        self._safe_queue_put("konveyor_dur", None)
    
    def konveyor_problem_var(self):
        self._safe_queue_put("konveyor_problem_var", None)

    def konveyor_problem_yok(self):
        self._safe_queue_put("konveyor_problem_yok", None)

    # Mesafe
    def mesafe_baslat(self):
        self._safe_queue_put("mesafe_baslat", None)

    def mesafe_bitir(self):
        self._safe_queue_put("mesafe_bitir", None)

    # Yönlendirici
    def yonlendirici_plastik(self):
        self._safe_queue_put("yonlendirici_plastik", None)

    def yonlendirici_cam(self):
        self._safe_queue_put("yonlendirici_cam", None)

    def yonlendirici_dur(self):
        self._safe_queue_put("yonlendirici_dur", None)

    # Klape (MEVCUT MANTIK KORUNDU)
    def klape_metal(self):
        self._safe_queue_put("klape_metal", None)
        self.klape_flag = True

    def klape_plastik(self):
        if self.klape_flag:
            self._safe_queue_put("klape_plastik", None)
            self.klape_flag = False

    # Sensör
    def yonlendirici_sensor_teach(self):
        self._safe_queue_put("yonlendirici_sensor_teach", None)

    def bme_sensor_veri(self):
        self._safe_queue_put("bme_sensor_veri", None)
    
    def sensor_saglik_durumu(self):
        self._safe_queue_put("sensor_saglik_durumu", None)
    
    def atik_uzunluk(self):
        self._safe_queue_put("atik_uzunluk", None)

    def ping(self):
        """Ping - sadece mevcut bağlantıyı test et, port arama yapma"""
        if not self._is_port_ready():
            log_warning(f"{self.cihaz_adi} port hazır değil - ping atlanıyor")
            return False
        
        # Mevcut bağlantıyı test et
        self.saglikli = False
        self._safe_queue_put("ping", None)
        time.sleep(self.PING_TIMEOUT)
        
        if not self.saglikli:
            log_warning(f"{self.cihaz_adi} ping başarısız - port arama yapılmıyor")
            # PORT ARAMA YAPMA! Sadece sağlık durumunu false yap
            return False
        
        return True

    def getir_saglik_durumu(self):
        """Sağlık durumu"""
        return self.saglikli

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
                
                # Özel parametre gönderme
                if command == "parametre_gonder":
                    self._send_parameters()
                elif command in komutlar:
                    self.seri_nesnesi.write(komutlar[command])
                    self.seri_nesnesi.flush()
                
            except (serial.SerialException, OSError) as e:
                log_error(f"{self.cihaz_adi} yazma hatası: {e}")
                self._handle_connection_error()
                break
            except Exception as e:
                log_exception(f"{self.cihaz_adi} yazma thread hatası", exc_info=(type(e), e, e.__traceback__))

    def _send_parameters(self):
        """Motor parametrelerini gönder"""
        try:
            params = [
                f"kh{self.konveyor_hizi}\n",
                f"yh{self.yonlendirici_hizi}\n",
                f"sh{self.klape_hizi}\n"
            ]
            
            for param in params:
                self.seri_nesnesi.write(param.encode())
                self.seri_nesnesi.flush()
                time.sleep(0.05)
            
            log_system(f"Motor parametreleri gönderildi: K:{self.konveyor_hizi} Y:{self.yonlendirici_hizi} S:{self.klape_hizi}")
            
        except Exception as e:
            log_error(f"Parametre gönderme hatası: {e}")

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
            
            # Thread'leri durdur
            self.dinlemeyi_durdur()
            
            # Portu kapat
            with self._port_lock:
                if self.seri_nesnesi and self.seri_nesnesi.is_open:
                    try:
                        self.seri_nesnesi.close()
                    except:
                        pass
                self.seri_nesnesi = None
                self.saglikli = False
            
            # Yeniden bağlan
            threading.Thread(
                target=self._reconnect_worker,
                daemon=True,
                name=f"{self.cihaz_adi}_reconnect"
            ).start()
            
        except Exception as e:
            log_exception(f"{self.cihaz_adi} hata yönetimi başarısız", exc_info=(type(e), e, e.__traceback__))

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
                    time.sleep(1)
                    self.parametre_gonder()  # Motor parametrelerini tekrar gönder
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
            # Motor kontrol
            "motorlari_aktif_et": b"aktif\n",
            "motorlari_iptal_et": b"iptal\n",
            
            # Konveyör
            "konveyor_ileri": b"kmi\n",
            "konveyor_geri": b"kmg\n",
            "konveyor_dur": b"kmd\n",
            "konveyor_problem_var": b"pv\n",
            "konveyor_problem_yok": b"py\n",
            
            # Mesafe
            "mesafe_baslat": b"mb\n",
            "mesafe_bitir": b"ms\n",
            
            # Yönlendirici
            "yonlendirici_plastik": b"ymp\n",
            "yonlendirici_cam": b"ymc\n",
            "yonlendirici_dur": b"ymd\n",
            "yonlendirici_sensor_teach": b"yst\n",
            
            # Klape
            "klape_metal": b"smm\n",
            "klape_plastik": b"smp\n",
            
            # Sensör
            "bme_sensor_veri": b"bme\n",
            "sensor_saglik_durumu": b"msd\n",
            "atik_uzunluk": b"au\n",
            
            # Sistem
            "ping": b"ping\n",
            "reset": b"reset\n"
        }