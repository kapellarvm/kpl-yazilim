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
from rvm_sistemi.makine.seri.system_state_manager import system_state, CardState, SystemState
from rvm_sistemi.makine.seri.port_saglik_servisi import SaglikDurumu
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
        
        # Reset bypass için ping zamanı takibi
        self._last_ping_time = time.time()  # Başlangıç zamanı
        self._first_connection = True  # İlk bağlantı takibi
        
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
            system_state.set_card_state(self.cihaz_adi, CardState.CONNECTED, f"Port açıldı: {self.port_adi}")
            self.dinlemeyi_baslat()
            
            # Thread'lerin başlamasını bekle
            time.sleep(1)  # Thread'lerin başlaması için bekle
            
            # Thread'lerin düzgün başladığından emin ol
            if not self._is_port_ready():
                log_warning(f"{self.cihaz_adi} thread'ler düzgün başlamamış, yeniden başlatılıyor")
                self.dinlemeyi_durdur()
                time.sleep(0.5)
                self.dinlemeyi_baslat()
                time.sleep(1)  # Tekrar bekle
            
            # İlk bağlantıda reset komutu gönder
            print("OOOOOOOOOOOOOOOO-MOTOR RESET GİTTİ-OOOOOOOOOOOOO")
            log_system(f"{self.cihaz_adi} ilk bağlantı - reset komutu gönderiliyor")
            self._safe_queue_put("reset", None)
            time.sleep(2)  # Reset komutunun işlenmesi için bekle
            
            # RESET SONRASI STATUS TEST
            print("OOOOOOOOOOOOOOOO-MOTOR STATUS TEST GİTTİ-OOOOOOOOOOOOO")
            log_system(f"{self.cihaz_adi} reset sonrası status test gönderiliyor")
            self._safe_queue_put("status", None)
            time.sleep(1)  # Status test cevabı için bekle
            
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
                
                # Port bulundu, bağlantı kurmayı dene
                if self._try_connect_to_port():
                    log_success(f"{self.cihaz_adi} bağlantı kuruldu: {self.port_adi}")
                    
                    # Bağlantı kurulduktan sonra thread'lerin düzgün çalıştığından emin ol
                    time.sleep(0.5)  # Thread'lerin başlaması için bekle
                    if not self._is_port_ready():
                        log_warning(f"{self.cihaz_adi} thread'ler düzgün başlamamış, yeniden başlatılıyor")
                        self.dinlemeyi_durdur()
                        time.sleep(0.5)
                        self.dinlemeyi_baslat()
                        time.sleep(0.5)
                    
                    # Reset komutu _try_connect_to_port'ta gönderiliyor
                    
                    return True
                else:
                    log_warning(f"{self.cihaz_adi} port bulundu ama bağlantı kurulamadı: {self.port_adi}")
                    # Port bulundu ama bağlantı kurulamadı - port sağlık servisine bildir
                    system_state.set_card_state(self.cihaz_adi, CardState.ERROR, f"Port bulundu ama bağlantı kurulamadı: {self.port_adi}")
                    return False
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
        """Motorları aktif et - detaylı log ile"""
        log_system(f"{self.cihaz_adi} motorları aktif etme komutu gönderiliyor...")
        self._safe_queue_put("motorlari_aktif_et", None)
        log_system(f"{self.cihaz_adi} motorları aktif etme komutu queue'ya eklendi")

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
        
        # Ping zamanını hemen kaydet (reset bypass için)
        self._last_ping_time = time.time()
        
        # Mevcut sağlık durumunu kaydet
        previous_health = self.saglikli
        
        # Ping gönder
        self._safe_queue_put("ping", None)
        
        # PONG cevabını bekle (daha uzun süre)
        time.sleep(self.PING_TIMEOUT * 2)  # 0.6 saniye bekle
        
        # Eğer sağlık durumu değiştiyse (PONG geldi), başarılı
        if self.saglikli:
            log_system(f"{self.cihaz_adi} ping başarılı")
            return True
        
        # PONG gelmedi, başarısız
        log_warning(f"{self.cihaz_adi} ping başarısız - port arama yapılmıyor")
        return False

    def status_test(self):
        """Status test - 's' komutu ile motor kartının çalışır durumda olup olmadığını test et"""
        if not self._is_port_ready():
            log_warning(f"{self.cihaz_adi} port hazır değil - status test atlanıyor")
            return False
        
        # Status test için özel flag
        self._status_test_pending = True
        self._status_test_result = False
        
        # 's' komutu gönder
        self._safe_queue_put("status", None)
        
        # 'motor' cevabını bekle
        time.sleep(1.0)  # 1 saniye bekle
        
        # Sonucu kontrol et
        if hasattr(self, '_status_test_result') and self._status_test_result:
            log_system(f"{self.cihaz_adi} status test başarılı - motor cevabı alındı")
            return True
        else:
            log_warning(f"{self.cihaz_adi} status test başarısız - motor cevabı alınamadı")
            return False

    def getir_saglik_durumu(self):
        """Sağlık durumu"""
        return self.saglikli
    
    def thread_durumu_kontrol(self):
        """Thread durumunu kontrol et ve logla"""
        log_system(f"{self.cihaz_adi} thread durumu:")
        log_system(f"  - running: {self.running}")
        log_system(f"  - listen_thread: {self.listen_thread.is_alive() if self.listen_thread else 'None'}")
        log_system(f"  - write_thread: {self.write_thread.is_alive() if self.write_thread else 'None'}")
        log_system(f"  - port açık: {self.seri_nesnesi.is_open if self.seri_nesnesi else False}")
        log_system(f"  - port hazır: {self._is_port_ready()}")
        log_system(f"  - queue boyutu: {self.write_queue.qsize()}")
        return {
            'running': self.running,
            'listen_thread': self.listen_thread.is_alive() if self.listen_thread else False,
            'write_thread': self.write_thread.is_alive() if self.write_thread else False,
            'port_open': self.seri_nesnesi.is_open if self.seri_nesnesi else False,
            'port_ready': self._is_port_ready(),
            'queue_size': self.write_queue.qsize()
        }
    
    def motor_durumu_test(self):
        """Motor durumunu test et"""
        log_system(f"{self.cihaz_adi} motor durumu testi başlatılıyor...")
        
        # 1. Thread durumu
        thread_durum = self.thread_durumu_kontrol()
        
        # 2. Motor aktif etme komutu gönder
        log_system(f"{self.cihaz_adi} motorları aktif etme komutu gönderiliyor...")
        self.motorlari_aktif_et()
        time.sleep(2)  # Komutun işlenmesi için bekle
        
        # 3. Ping test
        log_system(f"{self.cihaz_adi} ping testi yapılıyor...")
        ping_sonuc = self.ping()
        
        # 4. Status test
        log_system(f"{self.cihaz_adi} status testi yapılıyor...")
        status_sonuc = self.status_test()
        
        log_system(f"{self.cihaz_adi} motor durumu testi tamamlandı:")
        log_system(f"  - Thread durumu: {thread_durum}")
        log_system(f"  - Ping sonucu: {ping_sonuc}")
        log_system(f"  - Status sonucu: {status_sonuc}")
        
        return {
            'thread_durum': thread_durum,
            'ping_sonuc': ping_sonuc,
            'status_sonuc': status_sonuc
        }

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
            
            # Port açık değilse thread başlatma
            if not self.seri_nesnesi or not self.seri_nesnesi.is_open:
                log_warning(f"{self.cihaz_adi} port açık değil - thread başlatılamıyor")
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
            # Kritik komutlar için özel işlem
            critical_commands = ["reset", "parametre_gonder", "motorlari_aktif_et", "motorlari_iptal_et"]
            
            if command in critical_commands:
                # Kritik komutlar için queue'yu temizle
                if self.write_queue.full():
                    # Queue'yu tamamen temizle
                    while not self.write_queue.empty():
                        try:
                            self.write_queue.get_nowait()
                        except queue.Empty:
                            break
                    log_warning(f"{self.cihaz_adi} kritik komut için queue temizlendi: {command}")
            else:
                # Normal komutlar için eski komutları at
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
        consecutive_write_errors = 0
        
        log_system(f"{self.cihaz_adi} yazma thread'i başlatıldı")
        
        while self.running:
            try:
                # Komut al
                try:
                    command, data = self.write_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                if command == "exit":
                    break
                
                # Port kontrolü - detaylı log
                if not self._is_port_ready():
                    log_warning(f"{self.cihaz_adi} port hazır değil - komut bekleniyor: {command}")
                    log_warning(f"  - seri_nesnesi: {self.seri_nesnesi is not None}")
                    log_warning(f"  - port açık: {self.seri_nesnesi.is_open if self.seri_nesnesi else False}")
                    log_warning(f"  - running: {self.running}")
                    time.sleep(0.1)
                    continue
                
                # Özel parametre gönderme
                if command == "parametre_gonder":
                    log_system(f"{self.cihaz_adi} parametre gönderiliyor...")
                    self._send_parameters()
                elif command in komutlar:
                    log_system(f"{self.cihaz_adi} komut gönderiliyor: {command}")
                    self.seri_nesnesi.write(komutlar[command])
                    self.seri_nesnesi.flush()
                    log_success(f"{self.cihaz_adi} komut başarıyla gönderildi: {command}")
                    consecutive_write_errors = 0  # Başarılı yazma
                else:
                    log_warning(f"{self.cihaz_adi} bilinmeyen komut: {command}")
                
            except (serial.SerialException, OSError) as e:
                consecutive_write_errors += 1
                log_error(f"{self.cihaz_adi} yazma hatası ({consecutive_write_errors}): {e}")
                
                # Çok fazla ardışık yazma hatası varsa reconnection başlat
                if consecutive_write_errors >= 3:
                    log_warning(f"{self.cihaz_adi} çok fazla yazma hatası - reconnection başlatılıyor")
                    
                    # System state kontrolü - eğer sistem meşgulse port sağlık servisine bildir
                    if system_state.is_system_busy():
                        log_warning(f"{self.cihaz_adi} sistem meşgul - port sağlık servisine bildiriliyor")
                        # Port sağlık servisine motor kartı sorunu bildir
                        self._notify_port_health_service()
                        break
                    else:
                        # Sistem meşgul değilse normal reconnection
                        self._handle_connection_error()
                        break
                else:
                    # Kısa süre bekle ve tekrar dene
                    time.sleep(0.5)
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
        
        # ESP32 boot mesajlarını bypass et
        if (message.startswith("ets") or 
            message.startswith("rst:") or 
            message.startswith("configsip:") or 
            message.startswith("clk_drv:") or 
            message.startswith("mode:") or 
            message.startswith("load:") or 
            message.startswith("entry") or
            message.startswith("E (") and "gpio:" in message):
            # ESP32 boot mesajları - bypass et
            log_system(f"{self.cihaz_adi} ESP32 boot mesajı bypass edildi: {message[:50]}...")
            return
        
        if message_lower == "pong":
            self.saglikli = True
        elif message_lower == "motor":
            # Status test sonucunu güncelle
            if hasattr(self, '_status_test_pending') and self._status_test_pending:
                self._status_test_result = True
                self._status_test_pending = False
                print("OOOOOOOOOOOOOOOO-MOTOR STATUS TEST BAŞARILI-OOOOOOOOOOOOO")
                log_system(f"{self.cihaz_adi} status test cevabı alındı: motor")
            else:
                print("OOOOOOOOOOOOOOOO-MOTOR STATUS TEST BAŞARILI-OOOOOOOOOOOOO")
                log_system(f"{self.cihaz_adi} status test cevabı alındı: motor")
        elif message_lower == "ykt":
            # Yönlendirici motor durumu
            log_system(f"{self.cihaz_adi} yönlendirici motor durumu: {message}")
        elif message_lower == "skt":
            # Sensör kartı durumu
            log_system(f"{self.cihaz_adi} sensör kartı durumu: {message}")
        elif message_lower == "ymk":
            # Yönlendirici motor konumu
            log_system(f"{self.cihaz_adi} yönlendirici motor konumu: {message}")
        elif message_lower in ["ykt", "skt", "ymk", "kmt", "smt"]:
            # Diğer motor durum mesajları
            log_system(f"{self.cihaz_adi} motor durum mesajı: {message}")
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
                self.saglikli = True  # Sağlıklı olarak işaretle
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
        """Bağlantı hatası yönetimi - System State Manager ile"""
        # System state manager ile reconnection kontrolü
        if not system_state.can_start_reconnection(self.cihaz_adi):
            log_warning(f"{self.cihaz_adi} reconnection zaten devam ediyor veya sistem meşgul")
            return
        
        # Reconnection başlat
        if not system_state.start_reconnection(self.cihaz_adi, "I/O Error"):
            log_warning(f"{self.cihaz_adi} reconnection başlatılamadı")
            return
        
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
            
            # Reconnection thread başlat (tek seferlik)
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

    def _notify_port_health_service(self):
        """Port sağlık servisine motor kartı sorunu bildir"""
        try:
            # Kart referanslarından port sağlık servisini al
            from .. import kart_referanslari
            port_saglik = kart_referanslari.port_saglik_servisi_al()
            
            if port_saglik:
                # Motor kartı için kritik durum oluştur
                port_saglik.kart_durumlari["motor"].durum = SaglikDurumu.KRITIK
                port_saglik.kart_durumlari["motor"].basarisiz_ping = port_saglik.MAX_PING_HATA
                
                log_system(f"{self.cihaz_adi} port sağlık servisine yazma hatası bildirildi")
                print(f"🔔 [MOTOR] Port sağlık servisine yazma hatası bildirildi")
            else:
                log_warning(f"{self.cihaz_adi} port sağlık servisi bulunamadı")
                
        except Exception as e:
            log_error(f"{self.cihaz_adi} port sağlık servisi bildirimi hatası: {e}")

    def _reconnect_worker(self):
        """Yeniden bağlanma worker'ı - System State Manager ile"""
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
                    time.sleep(1)
                    
                    # Reset komutu _try_connect_to_port'ta gönderiliyor
                    # Sonra parametreleri gönder
                    self.parametre_gonder()  # Motor parametrelerini tekrar gönder
                    self._connection_attempts = 0
                    log_success(f"{self.cihaz_adi} yeniden bağlandı ve resetlendi")
                    
                    # Bağlantı kurulduktan sonra thread'lerin düzgün çalıştığından emin ol
                    time.sleep(0.5)
                    if not self._is_port_ready():
                        log_warning(f"{self.cihaz_adi} reconnection sonrası thread'ler düzgün başlamamış, yeniden başlatılıyor")
                        self.dinlemeyi_durdur()
                        time.sleep(0.5)
                        self.dinlemeyi_baslat()
                        time.sleep(0.5)
                    
                    # Başarılı reconnection
                    system_state.finish_reconnection(self.cihaz_adi, True)
                    return
                
                time.sleep(delay)
            
            log_error(f"{self.cihaz_adi} yeniden bağlanamadı")
            # Başarısız reconnection
            system_state.finish_reconnection(self.cihaz_adi, False)
            
        except Exception as e:
            log_exception(f"{self.cihaz_adi} reconnection worker hatası", exc_info=(type(e), e, e.__traceback__))
            system_state.finish_reconnection(self.cihaz_adi, False)
        finally:
            # Thread kaydını sil
            system_state.unregister_thread(thread_name)

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
            "reset": b"reset\n",
            "status": b"s\n"
        }